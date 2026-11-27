# Treino da CNN de defeitos (sadio x com defeito)

Rede: ResNet-18 pré-treinada no ImageNet e ajustada às fotos da bancada (transferência de aprendizado). Entrada: recorte 224x224 do tomate, com balanço de branco.
Divisão sempre **por tomate**: fotos do mesmo tomate nunca ficam em treino e validação.

## Dataset

| Classe | Fotos | Tomates |
|---|---|---|
| sadio | 140 | 49 |
| com_defeito | 119 | 48 |

## Validação cruzada (5 dobras por tomate)

Cada dobra treina uma rede nova e valida em tomates que ela nunca viu. A média e o desvio padrão são a estimativa do desempenho em tomates novos.

| Dobra | Fotos | Melhor época | Acurácia | Acurácia balanceada | Sensibilidade (acha defeito) | Especificidade (passa sadio) | F1 |
|---|---|---|---|---|---|---|---|
| 1 | 52 | 24 | 90.4% | 90.5% | 91.7% | 89.3% | 89.8% |
| 2 | 52 | 22 | 96.2% | 96.1% | 95.8% | 96.4% | 95.8% |
| 3 | 52 | 28 | 94.2% | 94.3% | 95.8% | 92.9% | 93.9% |
| 4 | 52 | 8 | 94.2% | 94.3% | 95.8% | 92.9% | 93.9% |
| 5 | 51 | 30 | 92.2% | 92.5% | 95.7% | 89.3% | 91.7% |
| **Média** | | | **93.4%** | **93.6%** | **95.0%** | **92.1%** | **93.0%** |
| Desvio padrão | | | 2.0% | 1.9% | 1.7% | 2.7% | 2.1% |

Matriz de confusão somando as dobras (cada foto aparece uma vez, como validação):

| Real \ CNN | sadio | com_defeito |
|---|---|---|
| sadio | 129 | 11 |
| com_defeito | 6 | 113 |

Curvas de aprendizado: `curva_dobra_N.png` (e `historico_dobra_N.csv`). Recortes errados: `erros_validacao/` (p = probabilidade de defeito dada pela CNN).

## Modelo final (`cnn_defeito.onnx`, usado na IHM)

Treinado com **todos** os tomates por 24 épocas (mediana da melhor época das dobras, de no máximo 30). Com poucos tomates com defeito, separar alguns só para escolher a época tiraria exemplos que fazem falta; o desempenho esperado é o da validação cruzada acima.

> O resultado definitivo é o do conjunto de teste (2º lote), avaliado uma única vez.

