from typing import Dict, Protocol

from .channels import ChannelValues


class GainStrategy(Protocol):
    name: str

    def compute_gains(self, white_means: ChannelValues) -> ChannelValues: ...


class GreenReferenceGainStrategy:
    """Mantém o verde com ganho 1 e iguala vermelho e azul a ele.

    É o critério usado pelos processadores de imagem das câmeras: só corrige
    a cor, sem mudar o brilho geral da imagem.
    """

    name = "referencia_verde"

    def compute_gains(self, white_means: ChannelValues) -> ChannelValues:
        return ChannelValues(
            red=white_means.green / white_means.red,
            green=1.0,
            blue=white_means.green / white_means.blue,
        )


class TargetLevelGainStrategy:
    """Leva os três canais do branco ao mesmo nível alvo (ex.: 230).

    Corrige cor e brilho ao mesmo tempo. O alvo fica abaixo de 255 para que
    áreas mais claras que o gabarito não estourem depois do ganho.
    """

    name = "nivel_alvo"

    def __init__(self, target_level: float = 230.0):
        if not 0 < target_level <= 255:
            raise ValueError("O nível alvo precisa estar entre 0 e 255.")
        self._target_level = target_level

    def compute_gains(self, white_means: ChannelValues) -> ChannelValues:
        return ChannelValues(
            red=self._target_level / white_means.red,
            green=self._target_level / white_means.green,
            blue=self._target_level / white_means.blue,
        )


class GainStrategyFactory:
    _strategies: Dict[str, type] = {
        GreenReferenceGainStrategy.name: GreenReferenceGainStrategy,
        TargetLevelGainStrategy.name: TargetLevelGainStrategy,
    }

    @classmethod
    def available_names(cls) -> list:
        return list(cls._strategies)

    @classmethod
    def create(cls, name: str) -> GainStrategy:
        if name not in cls._strategies:
            raise ValueError(f"Estratégia '{name}' não existe. Opções: {', '.join(cls._strategies)}.")
        return cls._strategies[name]()
