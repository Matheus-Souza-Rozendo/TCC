# Classes de defeito — tomate cereja (CNN multilabel)

## ✅ Decisão: arquitetura multilabel

Cada tomate pode ter **vários defeitos ao mesmo tempo**. A CNN tem 1 saída por defeito, cada uma com **sigmoid** (não softmax).

| Saída | Defeito | Como reconhecer |
|---|---|---|
| 1 | **Rachado** | Fenda ou rachadura na pele (radial ou em anel) |
| 2 | **Podre / mofado** | Área mole, escura, aquosa ou com fungo |
| 3 | **Dano mecânico** | Amassado, furo, corte, pele esfolada |
| 4 | **Mancha** | Manchas sem rachadura (ex.: podridão apical, queimadura de sol) |

**Sadio não é uma saída:** sadio = nenhuma saída acima do limiar.

## O que muda no projeto

| Item | Multiclasse (antes) | Multilabel (agora) |
|---|---|---|
| Última camada | softmax, 5 saídas | sigmoid, 4 saídas |
| Função de perda | CrossEntropy | `BCEWithLogitsLoss` (com `pos_weight` para defeitos raros) |
| Rótulo na planilha | 1 coluna `defeito` | 1 coluna 0/1 por defeito: `rachado`, `podre`, `dano`, `mancha` |
| Decisão | maior probabilidade | cada saída ≥ limiar (ajustar o limiar por defeito na validação) |
| Métricas | acurácia, F1 | F1 por defeito, F1 macro, Hamming loss, matriz de confusão por defeito |

## Onde a prioridade ainda aparece

Não no rótulo, só na **classe final do tomate** (E9 — integração):
- Se `podre` ou `rachado` → **Descarte**
- Se só `dano` ou `mancha` → **2ª qualidade**
- Se nenhum → **1ª qualidade** (depois combina com cor e tamanho)

## Deformidade: tratar fora da CNN

Medida pela geometria do contorno (módulo de tamanho):
- **Circularidade** = 4π · área / perímetro² (1,0 = círculo perfeito)
- Se circularidade < limite (ex.: 0,85) → **Deformado** (vira mais um rótulo na saída final)

## Regras de rotulagem

- Marcar **todos** os defeitos visíveis (0 ou 1 em cada coluna).
- **Cálice NÃO é defeito:** fotografar tomates sadios com e sem cálice.
- **Na dúvida:** pasta `duvida/`, decidir depois.
- Ao dividir treino/val/teste, conferir que cada defeito aparece nos 3 conjuntos.

## Para conferir com o orientador

- [ ] Ok usar multilabel com 4 defeitos?
- [ ] Ok medir deformidade por geometria em vez de CNN?
