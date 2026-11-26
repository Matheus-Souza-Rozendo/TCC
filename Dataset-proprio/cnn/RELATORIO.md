# Treino da CNN de defeitos (sadio x com defeito)

Rede: ResNet-18 pré-treinada no ImageNet e ajustada às fotos da bancada (transferência de aprendizado). Entrada: recorte 224x224 do tomate, com balanço de branco.
Divisão sempre **por tomate**: fotos do mesmo tomate nunca ficam em treino e validação.

## Dataset

| Classe | Fotos | Tomates |
|---|---|---|
| sadio | 109 | 17 |
| com_defeito | 67 | 11 |

## Validação cruzada (5 dobras por tomate)

Cada dobra treina uma rede nova e valida em tomates que ela nunca viu. A média e o desvio padrão são a estimativa do desempenho em tomates novos.

| Dobra | Fotos | Melhor época | Acurácia | Acurácia balanceada | Sensibilidade (acha defeito) | Especificidade (passa sadio) | F1 |
|---|---|---|---|---|---|---|---|
| 1 | 35 | 30 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2 | 37 | 20 | 78.4% | 83.3% | 100.0% | 66.7% | 76.5% |
| 3 | 35 | 21 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 4 | 38 | 18 | 94.7% | 94.3% | 92.9% | 95.8% | 92.9% |
| 5 | 31 | 12 | 77.4% | 77.0% | 75.0% | 78.9% | 72.0% |
| **Média** | | | **90.1%** | **90.9%** | **93.6%** | **88.3%** | **88.3%** |
| Desvio padrão | | | 10.2% | 9.3% | 9.7% | 13.3% | 11.8% |

Matriz de confusão somando as dobras (cada foto aparece uma vez, como validação):

| Real \ CNN | sadio | com_defeito |
|---|---|---|
| sadio | 96 | 13 |
| com_defeito | 4 | 63 |

Curvas de aprendizado: `curva_dobra_N.png` (e `historico_dobra_N.csv`). Recortes errados: `erros_validacao/` (p = probabilidade de defeito dada pela CNN).

## Modelo final (`cnn_defeito.onnx`, usado na IHM)

Treinado com **todos** os tomates por 20 épocas (mediana da melhor época das dobras, de no máximo 30). Com poucos tomates com defeito, separar alguns só para escolher a época tiraria exemplos que fazem falta; o desempenho esperado é o da validação cruzada acima.

> O resultado definitivo é o do conjunto de teste (2º lote), avaliado uma única vez.

