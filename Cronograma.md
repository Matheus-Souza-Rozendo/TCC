# Classificador de Tomates Cereja — Requisitos e Cronograma

## 1. Objetivo

Desenvolver um sistema de visão computacional que classifica tomates cereja por:

- **Cor / maturação**: por LUT (Look-Up Table) de cores.
- **Defeitos e deformidades**: por CNN (rede neural convolucional).
- **Tamanho**: medição em milímetros com câmera fixa calibrada.

O sistema inclui uma ferramenta de treinamento (GUI) e uma IHM de operação. O trabalho é a base do TCC.

## 2. Escopo

| Dentro do escopo | Fora do escopo (trabalhos futuros) |
|---|---|
| Bancada com câmera fixa, iluminação controlada e fundo neutro | Integração completa com esteira industrial (CLP, atuadores, rejeito) |
| Classificação de 1 tomate por imagem (ou vários, separados) | Tomates sobrepostos ou encostados |
| Prova de conceito da velocidade para uso em esteira | Outras variedades de tomate |

## 3. Requisitos funcionais

| ID | Requisito | Critério de aceite |
|---|---|---|
| RF01 | Segmentar cada tomate do fundo da imagem | Máscara correta em ≥ 95% das imagens de teste |
| RF02 | Classificar a cor/maturação por LUT | 3 classes: imaturo (< 10% colorido), intermediário (10–60%), maduro (> 60%), agrupando os estágios USDA. Acurácia ≥ 90% |
| RF03 | Detectar defeitos por CNN multilabel e deformidade por geometria | 4 rótulos independentes (rachado, podre, dano mecânico, mancha); sadio = nenhum rótulo. F1 por defeito ≥ 0,85. Deformidade por circularidade do contorno |
| RF04 | Medir o diâmetro do tomate em mm | Erro médio absoluto ≤ 1 mm contra o paquímetro |
| RF05 | Calibrar a relação pixel → mm por região da imagem | Erro da calibração ≤ 0,5 mm em todas as regiões da imagem |
| RF06 | GUI de treinamento da LUT | Carregar imagens, marcar pixels/regiões por classe, gerar e salvar a LUT |
| RF07 | GUI de treinamento da CNN | Rotular imagens, separar os conjuntos, iniciar o treino, ver as métricas e salvar o modelo |
| RF08 | IHM de operação | Mostrar a imagem, a classe de cor, o defeito, o tamanho, a classe final e os contadores |
| RF09 | Registrar os resultados | Exportar CSV com data, imagem, cor, defeito, tamanho e classe final |

## 4. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | Tempo de processamento ≤ 200 ms por tomate (meta para uso em esteira) |
| RNF02 | Funcionar em PC comum (GPU opcional na inferência) |
| RNF03 | Resultados reproduzíveis: versionar o código, o dataset, a LUT e o modelo |
| RNF04 | Iluminação e posição da câmera fixas e documentadas |

## 5. Dataset

1. **Base pública**: usar um dataset público de tomates (ex.: Laboro Tomato, Kaggle) para o pré-treino e o aumento de dados.
2. **Fotos próprias**: fotografar na bancada final, com a mesma câmera e a mesma iluminação. Meta: ≥ 100 imagens por classe.
3. **Conjunto de teste exclusivo**: usar somente fotos próprias e nunca usá-las no treino.
   - Separar por tomate, não por foto: todas as fotos do mesmo tomate ficam no mesmo conjunto (para evitar vazamento de dados).
   - Medir cada tomate de teste com paquímetro (referência para o RF04).
4. **Divisão sugerida**: 70% treino / 15% validação / 15% teste.

## 6. Etapas, dependências e entregas

| # | Etapa | Depende de | Entrega |
|---|---|---|---|
| E1 | Revisão bibliográfica e definição das classes | — | Lista de classes, critérios, referências |
| E2 | Montagem da bancada (câmera, luz, fundo) | E1 | Bancada fixa documentada com fotos |
| E3 | Calibração pixel → mm (papel milimetrado por região da imagem) | E2 | Tabela/mapa de calibração + erro medido |
| E4 | Coleta e rotulagem do dataset | E1, E2 | Dataset versionado (treino/val/teste) |
| E5 | GUI de treinamento (LUT + CNN) | E1 | Ferramenta funcional |
| E6 | Segmentação + medição de tamanho | E3 | Módulo de tamanho validado (RF01, RF04) |
| E7 | Classificação de cor por LUT | E4, E5 | LUT treinada + métricas (RF02) |
| E8 | Treinamento da CNN de defeitos | E4, E5 | Modelo treinado + métricas (RF03) |
| E9 | Integração e IHM | E6, E7, E8 | Sistema completo (RF08, RF09) |
| E10 | Teste de efetividade | E9 | Matriz de confusão, acurácia, F1, erro de tamanho, tempo por tomate |
| E11 | Melhorias e prova de conceito em esteira | E10 | Teste de velocidade, análise de viabilidade |
| E12 | Escrita do TCC | Contínua | Texto final + apresentação |

## 7. Cronograma (semanas)

> Ajuste para as datas reais de início e de entrega do TCC.

| Etapa | S1–2 | S3–4 | S5–6 | S7–8 | S9–10 | S11–12 | S13–14 | S15–16 | S17–18 | S19–20 |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 Revisão e classes | ■ | | | | | | | | | |
| E2 Bancada | | ■ | | | | | | | | |
| E3 Calibração | | ■ | ■ | | | | | | | |
| E4 Dataset | | ■ | ■ | ■ | | | | | | |
| E5 GUI de treinamento | | | ■ | ■ | | | | | | |
| E6 Tamanho | | | | ■ | ■ | | | | | |
| E7 LUT de cor | | | | | ■ | ■ | | | | |
| E8 CNN de defeitos | | | | | ■ | ■ | ■ | | | |
| E9 Integração e IHM | | | | | | | ■ | ■ | | |
| E10 Teste de efetividade | | | | | | | | ■ | ■ | |
| E11 Melhorias / esteira | | | | | | | | | ■ | |
| E12 Escrita do TCC | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ | ■ |

**Marcos:**

- **S4**: bancada pronta e calibração feita.
- **S8**: dataset completo e GUI de treinamento funcionando.
- **S14**: LUT e CNN treinadas com métricas.
- **S16**: sistema integrado com IHM.
- **S18**: testes concluídos e resultados no texto.
- **S20**: TCC final entregue.

## 8. Riscos

| Risco | Mitigação |
|---|---|
| Poucas fotos de tomates com defeito | Coletar desde o início, usar aumento de dados e a base pública |
| Iluminação variável muda as cores da LUT | Iluminação fixa e difusa; balanço de branco travado na câmera |
| Distorção da lente nas bordas afeta o tamanho | Calibração por região (E3); se for preciso, calibração de câmera com tabuleiro de xadrez (OpenCV) |
| Atraso no treino da CNN | Usar transfer learning (ex.: MobileNet, ResNet) em vez de treinar do zero |
| Esteira fora do prazo | Manter a E11 como prova de conceito; o resto fica como trabalho futuro |
