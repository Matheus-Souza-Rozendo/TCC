# Treino da CNN de defeitos (sadio x com defeito)

Rede: ResNet-18 pré-treinada no ImageNet e ajustada às fotos da bancada (transferência de aprendizado). Entrada: recorte 224x224 do tomate, com balanço de branco.
Divisão sempre **por tomate**: fotos do mesmo tomate nunca ficam em treino e validação.

## Dataset

| Classe | Fotos | Tomates |
|---|---|---|
| sadio | 102 | 16 |
| com_defeito | 74 | 12 |

## Validação cruzada (5 dobras por tomate)

Cada dobra treina uma rede nova e valida em tomates que ela nunca viu. A média e o desvio padrão são a estimativa do desempenho em tomates novos.

| Dobra | Fotos | Melhor época | Acurácia | Acurácia balanceada | Sensibilidade (acha defeito) | Especificidade (passa sadio) | F1 |
|---|---|---|---|---|---|---|---|
| 1 | 32 | 20 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2 | 37 | 10 | 94.6% | 94.1% | 92.3% | 95.8% | 92.3% |
| 3 | 37 | 12 | 97.3% | 97.2% | 94.4% | 100.0% | 97.1% |
| 4 | 31 | 10 | 90.3% | 90.6% | 92.3% | 88.9% | 88.9% |
| 5 | 39 | 3 | 92.3% | 90.6% | 81.2% | 100.0% | 89.7% |
| **Média** | | | **94.9%** | **94.5%** | **92.1%** | **96.9%** | **93.6%** |
| Desvio padrão | | | 3.5% | 3.7% | 6.1% | 4.3% | 4.3% |

Matriz de confusão somando as dobras (cada foto aparece uma vez, como validação):

| Real \ CNN | sadio | com_defeito |
|---|---|---|
| sadio | 99 | 3 |
| com_defeito | 6 | 68 |

Curvas de aprendizado: `curva_dobra_N.png` (e `historico_dobra_N.csv`). Recortes errados: `erros_validacao/` (p = probabilidade de defeito dada pela CNN).

## Modelo final (`cnn_defeito.onnx`, usado na IHM)

Treinado com **todos** os tomates por 10 épocas (mediana da melhor época das dobras, de no máximo 30). Com poucos tomates com defeito, separar alguns só para escolher a época tiraria exemplos que fazem falta; o desempenho esperado é o da validação cruzada acima.

> O resultado definitivo é o do conjunto de teste (2º lote), avaliado uma única vez.

