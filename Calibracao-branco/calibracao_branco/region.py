from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RegionOfInterest:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("A região do gabarito precisa ter largura e altura positivas.")
        if self.x < 0 or self.y < 0:
            raise ValueError("A região do gabarito não pode ter coordenadas negativas.")

    @classmethod
    def from_text(cls, text: str) -> "RegionOfInterest":
        """Lê o formato 'x,y,largura,altura'."""
        values = [int(part) for part in text.split(",")]
        if len(values) != 4:
            raise ValueError("Use o formato x,y,largura,altura (ex.: 200,150,240,180).")
        return cls(*values)

    @classmethod
    def centered_in(cls, frame: np.ndarray) -> "RegionOfInterest":
        """Região central com 1/3 do quadro, usada quando o usuário não escolhe uma."""
        frame_height, frame_width = frame.shape[:2]
        width, height = frame_width // 3, frame_height // 3
        return cls(x=(frame_width - width) // 2, y=(frame_height - height) // 2, width=width, height=height)

    def crop(self, frame: np.ndarray) -> np.ndarray:
        frame_height, frame_width = frame.shape[:2]
        if self.x + self.width > frame_width or self.y + self.height > frame_height:
            raise ValueError(f"A região {self.to_text()} sai do quadro {frame_width}x{frame_height}.")
        return frame[self.y:self.y + self.height, self.x:self.x + self.width]

    def scaled(self, factor: float) -> "RegionOfInterest":
        """Converte entre a imagem da tela e a original.

        Arredonda para baixo para a região convertida nunca sair do quadro.
        """
        return RegionOfInterest(
            x=int(self.x * factor),
            y=int(self.y * factor),
            width=max(1, int(self.width * factor)),
            height=max(1, int(self.height * factor)),
        )

    def to_text(self) -> str:
        return f"{self.x},{self.y},{self.width},{self.height}"
