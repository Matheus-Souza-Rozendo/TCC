# Classes de cor (maturação) — tomate cereja

## Como a LUT vai funcionar (2 níveis)

1. **Nível do pixel (LUT):** a LUT diz a cor de cada pixel do tomate. Ela é **gerada por uma MLP**: a MLP é treinada com pixels marcados nas fotos da bancada e depois avaliada em todas as cores possíveis; o resultado é gravado na tabela. Na operação, só a LUT é usada, o que é rápido (consulta direta na tabela).
2. **Nível do tomate:** conta a % de pixels vermelhos na superfície e decide o estágio.

Isso é o mesmo princípio do artigo de Hou et al. (2024), que mede a maturação em % (≥ 90%, 80–90%, ≤ 80%).

## Nível 1 — Classes de pixel (o que você marca na GUI da LUT)

| Classe | Cor |
|---|---|
| Verde | verde / verde-claro |
| Amarelado | amarelo / laranja-claro |
| Rosado | rosa / laranja-avermelhado |
| Vermelho | vermelho |
| Fundo | tecido preto da bancada (será ignorado) |
| Cálice | talo/sépala verde-escura (será ignorado) |

## Nível 2 — Estágio do tomate (padrão USDA, 6 estágios)

| # | Estágio | Superfície não verde / vermelha |
|---|---|---|
| 1 | Verde (Green) | 0% — todo verde |
| 2 | Início de cor (Breaker) | até 10% |
| 3 | Virando (Turning) | 10% a 30% |
| 4 | Rosado (Pink) | 30% a 60% |
| 5 | Vermelho claro (Light red) | 60% a 90% |
| 6 | Vermelho (Red) | mais de 90% |

## ✅ Decisão: 3 classes (agrupando os estágios do USDA)

| Classe final | Estágios USDA | Superfície vermelha/colorida |
|---|---|---|
| **Imaturo** | 1–2 (Verde, Início de cor) | menos de 10% |
| **Intermediário** | 3–4 (Virando, Rosado) | 10% a 60% |
| **Maduro** | 5–6 (Vermelho claro, Vermelho) | mais de 60% |

**Por quê:** cada classe tem mais fotos, o rótulo fica menos subjetivo, e continua citável (é um agrupamento do padrão USDA).

**Regra no código:** `% colorido = (pixels amarelado + rosado + vermelho) / (pixels do tomate sem cálice)`.

## Para conferir com o orientador

- [ ] Ok usar 3 classes agrupadas do USDA?
- [ ] Os limites (10% e 60%) servem para tomate cereja?

## Referências

- USDA. *United States Standards for Grades of Fresh Tomatoes.* (tabela de estágios de cor)
- Hou, L. et al. *Tomato Sorting System Based on Machine Vision.* Electronics, 13, 2114, 2024. DOI: 10.3390/electronics13112114
