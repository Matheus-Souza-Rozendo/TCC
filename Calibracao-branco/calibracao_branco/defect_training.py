"""Treino da CNN de defeitos (sadio x com defeito) por transferência de aprendizado. Precisa do PyTorch.

Por que transferência: com poucas dezenas de tomates, uma rede treinada do zero
decora as fotos. A ResNet-18 já vem treinada no ImageNet (bordas, texturas,
manchas) e só é ajustada para os tomates da bancada.

A rede exportada (ONNX) já inclui a normalização e a softmax: na IHM basta
entregar o recorte RGB em 0..1 e ler a probabilidade de cada classe, só com o
OpenCV, sem PyTorch na bancada.
"""

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
import torch
from sklearn.model_selection import StratifiedGroupKFold
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision.models import ResNet18_Weights, resnet18
from torchvision.transforms import v2

from .binary_metrics import BinaryMetrics
from .errors import CalibrationError
from .image_files import load_image
from .labeled_capture import LabeledPhotoStore
from .tomato_crops import CROP_SIZE_PX, TomatoCropExtractor

CLASS_NAMES = ("sadio", "com_defeito")
DEFECT_CLASS = 1
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class TrainingSettings:
    epochs: int = 30
    batch_size: int = 16
    learning_rate: float = 1e-4
    weight_decay: float = 1e-4
    random_seed: int = 42


@dataclass(frozen=True)
class CropSample:
    crop_bgr: np.ndarray
    label: int
    tomato_id: int
    name: str


@dataclass(frozen=True)
class Prediction:
    sample: CropSample
    defect_probability: float

    @property
    def predicted_label(self) -> int:
        return int(self.defect_probability >= 0.5)

    def is_correct(self) -> bool:
        return self.predicted_label == self.sample.label


@dataclass(frozen=True)
class EpochRecord:
    epoch: int
    train_loss: float
    validation_loss: float
    validation_balanced_accuracy: float


@dataclass
class TrainingOutcome:
    model: nn.Module
    best_epoch: int
    history: List[EpochRecord] = field(default_factory=list)


def load_samples(store: LabeledPhotoStore, extractor: TomatoCropExtractor) -> List[CropSample]:
    samples = []
    for photo in store.labeled_photos():
        if not photo.path.is_file():
            print(f"AVISO: {photo.path.name} está no rotulos.csv mas o arquivo não existe; ignorada.")
            continue
        try:
            crop = extractor.largest_crop(load_image(photo.path))
        except CalibrationError as error:
            print(f"AVISO: {photo.path.name} ignorada ({str(error).splitlines()[0]}).")
            continue
        samples.append(CropSample(crop, 0 if photo.healthy else DEFECT_CLASS, photo.tomato_id, photo.path.stem))
    if not samples:
        raise CalibrationError("Nenhuma foto do dataset pôde ser recortada.")
    return samples


def cross_validation_folds(samples: List[CropSample], fold_count: int) -> List[Tuple[List[CropSample], List[CropSample]]]:
    folds = StratifiedGroupKFold(n_splits=fold_count, shuffle=True, random_state=TrainingSettings.random_seed)
    labels = [sample.label for sample in samples]
    groups = [sample.tomato_id for sample in samples]
    return [([samples[i] for i in train], [samples[i] for i in validation])
            for train, validation in folds.split(np.zeros(len(samples)), labels, groups)]


class NormalizedResNet(nn.Module):
    """ResNet-18 que recebe RGB em 0..1 e normaliza por dentro (vai junto no ONNX)."""

    def __init__(self):
        super().__init__()
        self.backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        self.backbone.fc = nn.Linear(self.backbone.fc.in_features, len(CLASS_NAMES))
        self.register_buffer("mean", torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1))
        self.register_buffer("std", torch.tensor(IMAGENET_STD).view(1, 3, 1, 1))

    def forward(self, rgb: torch.Tensor) -> torch.Tensor:
        return self.backbone((rgb - self.mean) / self.std)


class ProbabilityOutput(nn.Module):
    def __init__(self, classifier: nn.Module):
        super().__init__()
        self.classifier = classifier

    def forward(self, rgb: torch.Tensor) -> torch.Tensor:
        return torch.softmax(self.classifier(rgb), dim=1)


class CropTensorDataset(Dataset):
    def __init__(self, samples: Sequence[CropSample], transform: v2.Transform):
        self._samples = samples
        self._transform = transform

    def __len__(self) -> int:
        return len(self._samples)

    def __getitem__(self, index: int):
        sample = self._samples[index]
        rgb = torch.from_numpy(np.ascontiguousarray(sample.crop_bgr[..., ::-1])).permute(2, 0, 1)
        return self._transform(rgb), sample.label


def training_augmentation() -> v2.Transform:
    # O tomate cai em qualquer posição na bancada, então qualquer giro vale; a cor
    # varia pouco (luz calibrada), por isso o ajuste de brilho/contraste é pequeno.
    return v2.Compose([
        v2.RandomRotation(180),
        v2.RandomHorizontalFlip(),
        v2.RandomVerticalFlip(),
        v2.RandomResizedCrop(CROP_SIZE_PX, scale=(0.8, 1.0), ratio=(0.9, 1.1), antialias=True),
        v2.ToDtype(torch.float32, scale=True),
        v2.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
    ])


def evaluation_transform() -> v2.Transform:
    return v2.ToDtype(torch.float32, scale=True)


@dataclass
class TrainingRun:
    model: nn.Module
    loader: DataLoader
    optimizer: torch.optim.Optimizer
    loss_function: nn.Module


class DefectCnnTrainer:
    def __init__(self, settings: TrainingSettings, device: torch.device):
        self._settings = settings
        self._device = device

    def train(self, train_samples: List[CropSample], validation_samples: List[CropSample]) -> TrainingOutcome:
        run = self._new_run(train_samples)
        outcome = TrainingOutcome(run.model, best_epoch=0)
        best_score, best_state = (-1.0, float("-inf")), None
        for epoch in range(1, self._settings.epochs + 1):
            train_loss = self._train_one_epoch(run)
            validation_loss, validation_accuracy = self._validation_metrics(run.model, validation_samples)
            outcome.history.append(EpochRecord(epoch, train_loss, validation_loss, validation_accuracy))
            print(f"  época {epoch:2d}: perda treino {train_loss:.3f} | perda validação {validation_loss:.3f} | "
                  f"acurácia balanceada {validation_accuracy:.1%}")
            # Melhor época = maior acurácia balanceada; no empate, a de menor perda (a mais "segura").
            score = (validation_accuracy, -validation_loss)
            if score > best_score:
                best_score, best_state, outcome.best_epoch = score, _copy_state(run.model), epoch
        run.model.load_state_dict(best_state)
        return outcome

    def train_on_all(self, samples: List[CropSample], epochs: int) -> nn.Module:
        """Modelo final com todos os tomates, por um número de épocas já escolhido na validação cruzada.

        Com poucos tomates com defeito, separar 25% deles só para escolher a época
        tira exemplos que fazem falta; a validação cruzada já estimou o desempenho.
        """
        run = self._new_run(samples)
        for epoch in range(1, epochs + 1):
            print(f"  época {epoch:2d} de {epochs}: perda treino {self._train_one_epoch(run):.3f}")
        return run.model

    def predict(self, model: nn.Module, samples: Sequence[CropSample]) -> List[Prediction]:
        probabilities = self._probabilities(model, samples)
        return [Prediction(sample, float(p)) for sample, p in zip(samples, probabilities[:, DEFECT_CLASS])]

    def _new_run(self, train_samples: List[CropSample]) -> TrainingRun:
        torch.manual_seed(self._settings.random_seed)
        model = NormalizedResNet().to(self._device)
        return TrainingRun(
            model=model,
            loader=DataLoader(CropTensorDataset(train_samples, training_augmentation()),
                              batch_size=self._settings.batch_size, shuffle=True),
            optimizer=torch.optim.AdamW(model.parameters(), lr=self._settings.learning_rate,
                                        weight_decay=self._settings.weight_decay),
            loss_function=nn.CrossEntropyLoss(weight=self._class_weights(train_samples)),
        )

    def _class_weights(self, samples: List[CropSample]) -> torch.Tensor:
        # Peso inverso à quantidade: sem isso a rede "acerta" chutando sempre a classe mais comum.
        counts = np.bincount([s.label for s in samples], minlength=len(CLASS_NAMES)).astype(np.float32)
        weights = counts.sum() / (len(CLASS_NAMES) * np.maximum(counts, 1))
        return torch.tensor(weights, device=self._device)

    def _train_one_epoch(self, run: TrainingRun) -> float:
        run.model.train()
        losses = []
        for images, labels in run.loader:
            images, labels = images.to(self._device), labels.to(self._device)
            run.optimizer.zero_grad()
            loss = run.loss_function(run.model(images), labels)
            loss.backward()
            run.optimizer.step()
            losses.append(loss.item())
        return float(np.mean(losses))

    def _validation_metrics(self, model: nn.Module, samples: List[CropSample]) -> Tuple[float, float]:
        probabilities = self._probabilities(model, samples)
        labels = np.array([s.label for s in samples])
        log_loss = float(-np.mean(np.log(np.clip(probabilities[np.arange(len(labels)), labels], 1e-7, 1.0))))
        return log_loss, BinaryMetrics.from_labels(labels, probabilities.argmax(axis=1)).balanced_accuracy()

    @torch.no_grad()
    def _probabilities(self, model: nn.Module, samples: Sequence[CropSample]) -> np.ndarray:
        model.eval()
        loader = DataLoader(CropTensorDataset(samples, evaluation_transform()), batch_size=self._settings.batch_size)
        outputs = [torch.softmax(model(images.to(self._device)), dim=1).cpu() for images, _ in loader]
        return torch.cat(outputs).numpy()


def export_onnx(model: nn.Module, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Cópia: .cpu() move a rede no lugar, e quem chamou ainda pode estar usando a GPU.
    exported = ProbabilityOutput(copy.deepcopy(model)).cpu().eval()
    example = torch.zeros(1, 3, CROP_SIZE_PX, CROP_SIZE_PX)
    torch.onnx.export(exported, example, str(destination), input_names=["rgb"], output_names=["probabilidades"],
                      opset_version=17, dynamo=False)


def _copy_state(model: nn.Module) -> dict:
    return {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
