"""Divide o Laboro Tomato em train/val/test e recorta cada tomate por classe.

Uso:
    python preparar_laboro_tomato.py <pasta_extraida_do_zip> <pasta_de_saida>

Saída, para cada conjunto (train, val, test):
    <saida>/<conjunto>/images/            imagens inteiras
    <saida>/<conjunto>/annotations.json   anotações COCO só daquele conjunto
    <saida>/<conjunto>/recortes/<classe>/ um PNG por tomate, fundo preto pela máscara
    <saida>/CONTAGEM.md                   contagem por classe e conjunto

Decisões:
- O teste oficial do Laboro é mantido (comparável com outros trabalhos).
- A validação sai do treino oficial e fica com 15% do total de imagens.
- A divisão é por imagem: o mesmo tomate nunca aparece em dois conjuntos.
- Recortes com o fundo pintado de preto imitam o fundo da bancada (tecido preto).
"""

import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np

VALIDATION_FRACTION_OF_TOTAL = 0.15
RANDOM_SEED = 42
MINIMUM_CROP_SIDE_PX = 32
CROP_MARGIN_PX = 4
SPLIT_NAMES = ("train", "val", "test")


@dataclass(frozen=True)
class CocoSplit:
    images: List[dict]
    annotations: List[dict]
    categories: List[dict]
    image_folder: Path

    def annotations_by_image(self) -> Dict[int, List[dict]]:
        grouped = defaultdict(list)
        for annotation in self.annotations:
            grouped[annotation["image_id"]].append(annotation)
        return grouped

    def subset(self, image_ids: set) -> "CocoSplit":
        return CocoSplit(
            images=[image for image in self.images if image["id"] in image_ids],
            annotations=[annotation for annotation in self.annotations if annotation["image_id"] in image_ids],
            categories=self.categories,
            image_folder=self.image_folder,
        )


@dataclass
class SplitCounts:
    objects: Counter
    images_with_class: Counter
    crops: Counter
    crops_too_small: Counter
    image_count: int = 0


def load_split(annotation_file: Path, image_folder: Path) -> CocoSplit:
    data = json.loads(annotation_file.read_text(encoding="utf-8"))
    return CocoSplit(data["images"], data["annotations"], data["categories"], image_folder)


def split_train_into_train_and_validation(official_train: CocoSplit, total_images: int) -> Dict[str, CocoSplit]:
    image_ids = sorted(image["id"] for image in official_train.images)
    random.Random(RANDOM_SEED).shuffle(image_ids)
    validation_size = round(VALIDATION_FRACTION_OF_TOTAL * total_images)
    validation_ids = set(image_ids[:validation_size])
    return {
        "train": official_train.subset(set(image_ids) - validation_ids),
        "val": official_train.subset(validation_ids),
    }


def export_split(split: CocoSplit, destination: Path) -> SplitCounts:
    category_names = {category["id"]: category["name"] for category in split.categories}
    counts = SplitCounts(Counter(), Counter(), Counter(), Counter(), image_count=len(split.images))
    (destination / "images").mkdir(parents=True, exist_ok=True)
    annotations_by_image = split.annotations_by_image()
    for image_info in split.images:
        source = split.image_folder / image_info["file_name"]
        _link_or_copy(source, destination / "images" / Path(image_info["file_name"]).name)
        image_annotations = annotations_by_image[image_info["id"]]
        counts.images_with_class.update({category_names[a["category_id"]] for a in image_annotations})
        _export_crops(source, image_annotations, category_names, destination / "recortes", counts)
    _write_coco(split, destination / "annotations.json")
    return counts


def _export_crops(source: Path, annotations: List[dict], category_names: Dict[int, str],
                  crops_folder: Path, counts: SplitCounts) -> None:
    image = cv2.imdecode(np.fromfile(str(source), dtype=np.uint8), cv2.IMREAD_COLOR)
    for annotation in annotations:
        class_name = category_names[annotation["category_id"]]
        counts.objects[class_name] += 1
        x, y, width, height = (int(round(value)) for value in annotation["bbox"])
        if min(width, height) < MINIMUM_CROP_SIDE_PX:
            counts.crops_too_small[class_name] += 1
            continue
        crop = _masked_crop(image, annotation)
        output = crops_folder / class_name / f"{source.stem}_{annotation['id']}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(cv2.imencode(".png", crop)[1].tobytes())
        counts.crops[class_name] += 1


def _masked_crop(image: np.ndarray, annotation: dict) -> np.ndarray:
    """Recorte do tomate com tudo fora do contorno pintado de preto."""
    mask = np.zeros(image.shape[:2], np.uint8)
    for polygon in annotation["segmentation"]:
        points = np.array(polygon, dtype=np.float32).reshape(-1, 2).round().astype(np.int32)
        cv2.fillPoly(mask, [points], 255)
    x, y, width, height = (int(round(value)) for value in annotation["bbox"])
    top, left = max(0, y - CROP_MARGIN_PX), max(0, x - CROP_MARGIN_PX)
    bottom = min(image.shape[0], y + height + CROP_MARGIN_PX)
    right = min(image.shape[1], x + width + CROP_MARGIN_PX)
    crop = image[top:bottom, left:right].copy()
    crop[mask[top:bottom, left:right] == 0] = 0
    return crop


def _link_or_copy(source: Path, destination: Path) -> None:
    # Link físico não ocupa espaço extra no disco; se o sistema não permitir, copia.
    if destination.exists():
        return
    try:
        destination.hardlink_to(source)
    except OSError:
        shutil.copy2(source, destination)


def _write_coco(split: CocoSplit, destination: Path) -> None:
    data = {"images": split.images, "annotations": split.annotations, "categories": split.categories}
    destination.write_text(json.dumps(data), encoding="utf-8")


def write_report(counts_by_split: Dict[str, SplitCounts], class_names: List[str], destination: Path) -> str:
    total_images = sum(counts.image_count for counts in counts_by_split.values())
    lines = [
        "# Laboro Tomato — contagem por classe",
        "",
        "| Conjunto | Imagens | % |",
        "|---|---|---|",
    ]
    lines += [f"| {name} | {counts.image_count} | {counts.image_count / total_images:.0%} |"
              for name, counts in counts_by_split.items()]
    lines.append(f"| **total** | **{total_images}** | |")
    for title, attribute in (("Tomates anotados (objetos)", "objects"),
                             ("Imagens que contêm a classe", "images_with_class"),
                             (f"Recortes salvos (lado ≥ {MINIMUM_CROP_SIDE_PX} px)", "crops"),
                             (f"Tomates pequenos demais, sem recorte (lado < {MINIMUM_CROP_SIDE_PX} px)", "crops_too_small")):
        lines += ["", f"## {title}", "", "| Classe | " + " | ".join(SPLIT_NAMES) + " | total |",
                  "|---|" + "---|" * (len(SPLIT_NAMES) + 1)]
        for class_name in class_names:
            values = [getattr(counts_by_split[name], attribute)[class_name] for name in SPLIT_NAMES]
            lines.append(f"| {class_name} | " + " | ".join(str(v) for v in values) + f" | {sum(values)} |")
        totals = [sum(getattr(counts_by_split[name], attribute).values()) for name in SPLIT_NAMES]
        lines.append("| **total** | " + " | ".join(f"**{v}**" for v in totals) + f" | **{sum(totals)}** |")
    report = "\n".join(lines) + "\n"
    destination.write_text(report, encoding="utf-8")
    return report


def main(extracted_folder: Path, output_folder: Path) -> None:
    official_train = load_split(extracted_folder / "annotations" / "train.json", extracted_folder / "train")
    official_test = load_split(extracted_folder / "annotations" / "test.json", extracted_folder / "test")
    total_images = len(official_train.images) + len(official_test.images)
    splits = {**split_train_into_train_and_validation(official_train, total_images), "test": official_test}
    counts_by_split = {}
    for name in SPLIT_NAMES:
        print(f"Exportando {name} ({len(splits[name].images)} imagens)...")
        counts_by_split[name] = export_split(splits[name], output_folder / name)
    class_names = [category["name"] for category in official_train.categories]
    # Só o caminho: o console do Windows (cp1252) não imprime símbolos como "≥" do relatório.
    write_report(counts_by_split, class_names, output_folder / "CONTAGEM.md")
    print(f"Contagem salva em: {(output_folder / 'CONTAGEM.md').resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
