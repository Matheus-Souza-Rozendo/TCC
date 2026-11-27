# Conferência da LUT de cor

Maturação calculada pela regra do RF02 (imaturo: < 10% colorido; maduro: > 60% vermelho; senão intermediário; porcentagens sobre o tomate sem cálice) contra a maturação informada na captura.

## Tomates de validação (não usados no treino da MLP)

Acerto: **62%** (5 de 8 fotos)

| Informada \ Calculada | imaturo | intermediario | maduro |
|---|---|---|---|
| imaturo | 0 | 0 | 0 |
| intermediario | 0 | 0 | 3 |
| maduro | 0 | 0 | 5 |

## Tomates de treino (só conferência: a MLP já viu esses pixels)

Acerto: **62%** (26 de 42 fotos)

| Informada \ Calculada | imaturo | intermediario | maduro |
|---|---|---|---|
| imaturo | 4 | 0 | 0 |
| intermediario | 0 | 3 | 16 |
| maduro | 0 | 0 | 19 |

## Por foto

| Foto | Tomate | Conjunto | Informada | % colorido | % vermelho | Calculada | Acerto |
|---|---|---|---|---|---|---|---|
| tomate_0001_foto_01.jpg | 1 | treino | maduro | 100% | 87% | maduro | sim |
| tomate_0002_foto_01.jpg | 2 | treino | maduro | 100% | 95% | maduro | sim |
| tomate_0003_foto_01.jpg | 3 | treino | maduro | 100% | 89% | maduro | sim |
| tomate_0003_foto_02.jpg | 3 | treino | maduro | 100% | 89% | maduro | sim |
| tomate_0004_foto_01.jpg | 4 | treino | maduro | 100% | 89% | maduro | sim |
| tomate_0005_foto_01.jpg | 5 | treino | maduro | 100% | 83% | maduro | sim |
| tomate_0006_foto_01.jpg | 6 | treino | maduro | 100% | 94% | maduro | sim |
| tomate_0007_foto_01.jpg | 7 | treino | maduro | 100% | 89% | maduro | sim |
| tomate_0008_foto_01.jpg | 8 | treino | maduro | 100% | 94% | maduro | sim |
| tomate_0009_foto_01.jpg | 9 | treino | maduro | 100% | 89% | maduro | sim |
| tomate_0010_foto_01.jpg | 10 | validação | maduro | 100% | 87% | maduro | sim |
| tomate_0011_foto_01.jpg | 11 | treino | maduro | 100% | 89% | maduro | sim |
| tomate_0012_foto_01.jpg | 12 | treino | maduro | 100% | 95% | maduro | sim |
| tomate_0013_foto_01.jpg | 13 | treino | maduro | 100% | 78% | maduro | sim |
| tomate_0014_foto_01.jpg | 14 | validação | maduro | 100% | 94% | maduro | sim |
| tomate_0015_foto_01.jpg | 15 | validação | maduro | 100% | 97% | maduro | sim |
| tomate_0016_foto_01.jpg | 16 | treino | maduro | 100% | 90% | maduro | sim |
| tomate_0017_foto_01.jpg | 17 | treino | maduro | 100% | 91% | maduro | sim |
| tomate_0018_foto_01.jpg | 18 | treino | maduro | 100% | 90% | maduro | sim |
| tomate_0019_foto_01.jpg | 19 | treino | maduro | 100% | 93% | maduro | sim |
| tomate_0020_foto_02.jpg | 20 | validação | maduro | 100% | 94% | maduro | sim |
| tomate_0021_foto_01.jpg | 21 | treino | maduro | 100% | 93% | maduro | sim |
| tomate_0022_foto_01.jpg | 22 | validação | maduro | 100% | 93% | maduro | sim |
| tomate_0023_foto_01.jpg | 23 | treino | maduro | 100% | 90% | maduro | sim |
| tomate_0024_foto_01.jpg | 24 | validação | intermediario | 100% | 88% | maduro | **não** |
| tomate_0024_foto_02.jpg | 24 | validação | intermediario | 100% | 89% | maduro | **não** |
| tomate_0024_foto_03.jpg | 24 | validação | intermediario | 100% | 91% | maduro | **não** |
| tomate_0025_foto_01.jpg | 25 | treino | intermediario | 94% | 67% | maduro | **não** |
| tomate_0025_foto_02.jpg | 25 | treino | intermediario | 100% | 89% | maduro | **não** |
| tomate_0025_foto_03.jpg | 25 | treino | intermediario | 100% | 88% | maduro | **não** |
| tomate_0026_foto_01.jpg | 26 | treino | intermediario | 100% | 88% | maduro | **não** |
| tomate_0026_foto_02.jpg | 26 | treino | intermediario | 100% | 86% | maduro | **não** |
| tomate_0026_foto_03.jpg | 26 | treino | intermediario | 100% | 88% | maduro | **não** |
| tomate_0027_foto_01.jpg | 27 | treino | intermediario | 100% | 95% | maduro | **não** |
| tomate_0027_foto_02.jpg | 27 | treino | intermediario | 100% | 94% | maduro | **não** |
| tomate_0027_foto_03.jpg | 27 | treino | intermediario | 100% | 94% | maduro | **não** |
| tomate_0027_foto_04.jpg | 27 | treino | intermediario | 100% | 94% | maduro | **não** |
| tomate_0027_foto_05.jpg | 27 | treino | intermediario | 100% | 93% | maduro | **não** |
| tomate_0028_foto_01.jpg | 28 | treino | intermediario | 100% | 85% | maduro | **não** |
| tomate_0029_foto_01.jpg | 29 | treino | intermediario | 100% | 89% | maduro | **não** |
| tomate_0029_foto_02.jpg | 29 | treino | intermediario | 100% | 89% | maduro | **não** |
| tomate_0029_foto_05.jpg | 29 | treino | intermediario | 100% | 89% | maduro | **não** |
| tomate_0029_foto_06.jpg | 29 | treino | intermediario | 100% | 89% | maduro | **não** |
| tomate_0030_foto_01.jpg | 30 | treino | intermediario | 100% | 48% | intermediario | sim |
| tomate_0030_foto_02.jpg | 30 | treino | intermediario | 100% | 46% | intermediario | sim |
| tomate_0030_foto_03.jpg | 30 | treino | intermediario | 100% | 48% | intermediario | sim |
| tomate_0031_foto_01.jpg | 31 | treino | imaturo | 2% | 2% | imaturo | sim |
| tomate_0031_foto_02.jpg | 31 | treino | imaturo | 2% | 2% | imaturo | sim |
| tomate_0031_foto_03.jpg | 31 | treino | imaturo | 2% | 2% | imaturo | sim |
| tomate_0032_foto_01.jpg | 32 | treino | imaturo | 0% | 0% | imaturo | sim |

Imagens de conferência (foto | classes da LUT) em `conferencia/`. Cores: verde = verde, amarelo = amarelado, rosa = rosado, vermelho = vermelho, verde-escuro = cálice.
