# Dataset público: Laboro Tomato

Dataset escolhido para pré-treino e aumento de dados (planejamento, item "Base pública").
O conjunto de **teste do TCC continua sendo só de fotos próprias** da bancada.

| Item | Valor |
|---|---|
| Fonte | [github.com/laboroai/LaboroTomato](https://github.com/laboroai/LaboroTomato), Laboro.AI Inc., 2020 |
| Licença | **CC BY-NC-SA 4.0**: uso não comercial, com atribuição; derivados com a mesma licença |
| Download | `http://assets.laboro.ai.s3.amazonaws.com/laborotomato/laboro_tomato.zip` (1,65 GB) |
| Conteúdo | 804 fotos de estufa (3024×4032 e 3120×4160), 9.777 tomates com máscara (polígono COCO) |
| Classes | `b_` = tomate normal, `l_` = **tomate cereja**; maturação `green`, `half_ripened`, `fully_ripened` |

## Como gerar de novo

A pasta `Dataset/` não vai para o Git (3 GB). Para recriar:

```bash
curl -L -o Dataset/_download/laboro_tomato.zip http://assets.laboro.ai.s3.amazonaws.com/laborotomato/laboro_tomato.zip
python -c "import zipfile; zipfile.ZipFile('Dataset/_download/laboro_tomato.zip').extractall('Dataset/_extraido')"
python Preparacao-dataset/preparar_laboro_tomato.py Dataset/_extraido/laboro_tomato Dataset/laboro_tomato
```

A divisão é sempre a mesma (semente fixa = 42).

## Estrutura gerada

```text
Dataset/laboro_tomato/
  train/ val/ test/
    images/              fotos inteiras
    annotations.json     anotações COCO só daquele conjunto
    recortes/<classe>/   1 PNG por tomate, fundo preto pela máscara
  CONTAGEM.md
```

## Decisões

- **Teste oficial mantido** (161 imagens), para comparar com outros trabalhos que usam o Laboro.
- **Validação** = 15% do total (121 imagens), sorteadas do treino oficial. Divisão final: 65% / 15% / 20%.
- **Divisão por imagem**: o mesmo tomate nunca aparece em dois conjuntos. Conferido: nenhuma imagem repetida entre os conjuntos.
- **Recortes com fundo preto**: o que está fora da máscara vira preto, para parecer com o tecido preto da bancada.
  Recortes com lado < 32 px foram descartados (só 2 de 9.777).
- **Orientação EXIF**: 305 das 804 fotos dependem da rotação EXIF para bater com as anotações.
  O OpenCV (`cv2.imread`/`imdecode`) já aplica a rotação. No PIL, usar `ImageOps.exif_transpose` antes de usar as anotações.

## Contagem

Conferida com a tabela oficial do README do Laboro: **bate exatamente** (train + val = treino oficial; teste idêntico).

| Conjunto | Imagens | % |
|---|---|---|
| train | 522 | 65% |
| val | 121 | 15% |
| test | 161 | 20% |
| **total** | **804** | |

**Tomates por classe** (cada imagem tem vários tomates):

| Classe | train | val | test | total |
|---|---|---|---|---|
| b_fully_ripened | 281 | 67 | 72 | 420 |
| b_half_ripened | 431 | 89 | 116 | 636 |
| b_green | 1.216 | 251 | 387 | 1.854 |
| **l_fully_ripened** (cereja) | 815 | 167 | 269 | 1.251 |
| **l_half_ripened** (cereja) | 619 | 178 | 223 | 1.020 |
| **l_green** (cereja) | 2.999 | 668 | 929 | 4.596 |
| **total** | **6.361** | **1.420** | **1.996** | **9.777** |

**Imagens que contêm a classe:**

| Classe | train | val | test | total |
|---|---|---|---|---|
| b_fully_ripened | 151 | 35 | 40 | 226 |
| b_half_ripened | 186 | 45 | 52 | 283 |
| b_green | 257 | 55 | 71 | 383 |
| l_fully_ripened | 200 | 50 | 59 | 309 |
| l_half_ripened | 187 | 51 | 67 | 305 |
| l_green | 227 | 55 | 69 | 351 |

Recortes salvos: os mesmos números da tabela de tomates, menos 2 `l_green` pequenos demais no train (9.775 no total).

## Cuidados ao usar no TCC

1. **Os limiares de maturação não são os mesmos do RF02.**

   | Laboro | % vermelho | RF02 do TCC | % colorido |
   |---|---|---|---|
   | green | 0–30% | imaturo | < 10% |
   | half_ripened | 30–89% | intermediário | 10–60% |
   | fully_ripened | ≥ 90% | maduro | > 60% |

   Um tomate com 70% de vermelho é `half_ripened` no Laboro e **maduro** no TCC. Por isso, **não usar o rótulo do Laboro direto como rótulo do TCC.**
   Usar os recortes para treinar a **LUT por pixel**, que não depende desses limiares, ou reclassificar os recortes pela regra do TCC (% de pixels coloridos).
2. **Classe desbalanceada:** `l_green` tem 4,5× mais exemplos que `l_half_ripened`.
3. **Não tem defeitos.** Para o RF03, o complemento mais próximo é o TFDD (Mendeley, com a classe *Fruit Cracking*), mas ele é pequeno e não é de tomate cereja.
4. **Domínio diferente da bancada:** fotos de estufa, com o tomate no pé, folhas na frente e luz natural. Muitos recortes estão parcialmente escondidos.
   Serve para pré-treino; a avaliação final é só com fotos próprias.
5. **Citação:** Laboro.AI Inc. *Laboro Tomato: Instance segmentation dataset*. 2020. Disponível em: https://github.com/laboroai/LaboroTomato.
