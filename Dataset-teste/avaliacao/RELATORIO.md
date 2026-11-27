# Avaliação no lote de teste

Tomates no lote: **22** (uma foto por tomate). Não segmentados: 0.
Nenhum destes tomates foi usado no treino da LUT nem da CNN. Intervalos de confiança de 95% pelo método de Wilson; com poucos tomates eles são largos, e é isso que o resultado permite afirmar.

## CNN de defeitos (sadio x com defeito)

| Métrica | Valor |
|---|---|
| Acurácia | 86.4% (19/22; IC 95%: 66.7% a 95.3%) |
| Sensibilidade (acha o defeito) | 84.6% (11/13; IC 95%: 57.8% a 95.7%) |
| Especificidade (passa o sadio) | 88.9% (8/9; IC 95%: 56.5% a 98.0%) |
| Acurácia balanceada | 86.8% |
| Precisão | 91.7% |
| F1 | 88.0% |

| Real \ CNN | sadio | com defeito |
|---|---|---|
| sadio | 8 | 1 |
| com defeito | 2 | 11 |

## LUT de cor (maturação)

Regra: imaturo se < 10% da superfície colorida; maduro se > 60% vermelha; senão intermediário. Avaliada em todos os tomates, com ou sem defeito.

Acerto: 86.4% (19/22; IC 95%: 66.7% a 95.3%)

| Real \ LUT | imaturo | intermediario | maduro |
|---|---|---|---|
| imaturo | 0 | 1 | 0 |
| intermediario | 0 | 2 | 2 |
| maduro | 0 | 0 | 17 |

## Destino final (o que a bancada faria)

Esperado: com defeito -> Descarte; sadio -> classe de maturação do rótulo.

Acerto: 81.8% (18/22; IC 95%: 61.5% a 92.7%)

## Tamanho e tempo

Sem diâmetro de paquímetro nos rótulos, o tamanho não tem referência para erro; fica a distribuição medida.

| Medida | Mínimo | Mediana | Máximo |
|---|---|---|---|
| Diâmetro equivalente (mm) | 18.87 | 26.24 | 32.16 |
| Circularidade | 0.51 | 0.79 | 0.86 |
| Tempo por foto (ms) | 50.65 | 53.51 | 56.67 |

Fotos com objetos extras segmentados: 0.
O tempo é deste computador (inclui balanço de branco, segmentação, LUT e CNN).

## Por tomate

| Tomate | Maturação real | LUT | % vermelho | Defeito real | P(defeito) | Destino real | Destino sistema | Diâmetro (mm) |
|---|---|---|---|---|---|---|---|---|
| 1 | maduro | maduro | 100% | não | 0.02 | Maduro | Maduro | 24.0 |
| 2 | intermediario | maduro | 91% | sim | 0.88 | Descarte | Descarte | 27.3 |
| 3 | imaturo | intermediario | 25% | não | 0.37 | Imaturo | Intermediário ❌ | 27.2 |
| 4 | maduro | maduro | 96% | não | 0.24 | Maduro | Maduro | 26.7 |
| 5 | maduro | maduro | 98% | não | 0.01 | Maduro | Maduro | 27.7 |
| 6 | maduro | maduro | 76% | sim | 0.61 | Descarte | Descarte | 28.3 |
| 7 | maduro | maduro | 96% | sim | 0.03 | Descarte | Maduro ❌ | 27.7 |
| 8 | intermediario | intermediario | 55% | não | 0.08 | Intermediário | Intermediário | 27.0 |
| 9 | maduro | maduro | 96% | sim | 0.99 | Descarte | Descarte | 22.3 |
| 10 | maduro | maduro | 95% | sim | 0.76 | Descarte | Descarte | 26.3 |
| 11 | maduro | maduro | 85% | sim | 1.00 | Descarte | Descarte | 21.0 |
| 12 | maduro | maduro | 93% | sim | 1.00 | Descarte | Descarte | 18.9 |
| 13 | maduro | maduro | 97% | sim | 0.90 | Descarte | Descarte | 26.8 |
| 14 | intermediario | intermediario | 60% | sim | 0.89 | Descarte | Descarte | 25.3 |
| 15 | maduro | maduro | 99% | sim | 0.98 | Descarte | Descarte | 24.6 |
| 16 | maduro | maduro | 100% | não | 0.72 | Maduro | Descarte ❌ | 32.2 |
| 17 | maduro | maduro | 96% | não | 0.14 | Maduro | Maduro | 27.9 |
| 18 | maduro | maduro | 100% | não | 0.06 | Maduro | Maduro | 23.6 |
| 19 | maduro | maduro | 100% | não | 0.01 | Maduro | Maduro | 26.1 |
| 20 | intermediario | maduro | 91% | sim | 0.61 | Descarte | Descarte | 24.8 |
| 21 | maduro | maduro | 98% | sim | 0.99 | Descarte | Descarte | 20.8 |
| 22 | maduro | maduro | 99% | sim | 0.19 | Descarte | Maduro ❌ | 23.1 |

