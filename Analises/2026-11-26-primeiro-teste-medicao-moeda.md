# Análise — primeiro teste de medição com moeda (26/11/2026)

> Dados: commits `bd1c5d3` (calibrações) e `bbb3e8b` (medições), vindos do PC da bancada.
> Arquivos: `Calibracao-branco/bancada.gain`, `Calibracao-branco/bancada_escala.png`, `Calibracao-branco/medicoes/`.
> Os valores das 24 medições foram lidos das imagens de resultado. A leitura foi conferida rodando a medição de
> novo nas 2 fotos `_original`: o resultado foi idêntico (26,78 e 26,74 mm).

## Resumo

| Pergunta | Resposta |
|---|---|
| A correção por região ajuda? | **Sim.** A diferença entre posições caiu de 1,08 mm para 0,56 mm (quase metade). |
| O sistema é repetível? | **Sim, muito.** Na mesma posição, desvio padrão de 0,01 a 0,03 mm. |
| Atende o RF04 (erro médio ≤ 1 mm)? | **Sim, com folga:** erro médio absoluto de 0,46 mm com correção. |
| Está tudo certo? | **Não.** Todas as medidas ficaram **abaixo** do real (viés de −0,46 a −0,53 mm). É um erro sistemático da **calibração de escala**, não da segmentação. |
| Precisa de mais amostras? | **Sim, mas primeiro corrigir a causa do viés.** Repetir a moeda no mesmo lugar não acrescenta informação: das 24 medições, 13 estão em só 2 posições. Ver [Próximos passos](#próximos-passos). |

## 1. Calibração de branco (`calibrar.bat`, 13:20)

| Item | Valor | Leitura |
|---|---|---|
| Estratégia | `nivel_alvo` (branco → 230) | ok |
| Média do branco (R, G, B) | 98,8 / 129,6 / 155,4 | **Escuro e azulado**: a luz é fria e a exposição está baixa |
| Ganhos (R, G, B) | **2,33** / 1,78 / 1,48 | Ganho alto no vermelho amplifica o ruído desse canal |
| Variação no gabarito | R **14,7%**, G 6,7%, B 3,3% | Acima do limite de 8% (o programa gravou um AVISO) |

**Por que importa:** a classificação de maturação (LUT) depende principalmente do **vermelho**. Com ganho de 2,3, o ruído do canal vermelho também é multiplicado por 2,3. A variação de 14,7% no vermelho indica luz não uniforme, ou região com sombra ou reflexo.

**Ação:** aumentar a luz ou a exposição até o branco ficar com G ≈ 200 (ganhos perto de 1,1 a 1,3). Conferir se a luz é difusa. Se der, usar uma lâmpada de temperatura neutra (≈ 5000 K).

> Também há um `Bancada/bancada.gain` mais antigo (12:49, outra região, sem escala). O arquivo em uso é o `Calibracao-branco/bancada.gain`. Apagar o antigo para não confundir.

## 2. Calibração de escala (`calibrar_escala.bat`, 13:29)

Tabuleiro calib.io "Checker Size 15 mm", 10×7 cantos detectados, região 938×588 px (≈ 188×118 mm), grade 3×3.

| mm/pixel | coluna 0 | coluna 1 | coluna 2 |
|---|---|---|---|
| **linha 0** (topo) | 0,2024 | 0,2038 | 0,2032 |
| **linha 1** | 0,1998 | 0,2012 | 0,2023 |
| **linha 2** (baixo) | 0,1966 | 0,1978 | 0,2004 |

- Média 0,2008 mm/px. Resolução 1920×1080: 1 pixel ≈ 0,2 mm.
- Erro máximo 0,46 mm (célula 2_2), **dentro do RF05 (0,5 mm), mas no limite**. As células da linha de baixo têm o maior erro.
- Variação de **3,6%** de cima para baixo e menor da esquerda para a direita. Um degradê linear assim é típico de **câmera não perpendicular** ao plano (perspectiva), e não de distorção da lente (que seria simétrica a partir do centro).
- Poucos trechos por célula (10 a 21): o tabuleiro mal cobre a região, principalmente nos cantos.

## 3. Medições da moeda de R$ 1 (diâmetro nominal 27,00 mm)

24 medições entre 13:53 e 14:07, em 10 posições diferentes. Uma delas (14:04:30) foi feita sem informar o diâmetro real.

### Dados

| Hora | px | Sem correção (mm) | Com correção (mm) | Células |
|---|---|---|---|---|
| 13:53:33 | 131,9 | 26,49 | 26,54 | 1_1 |
| 13:55:30 | 132,8 | 26,67 | 26,41 | 1_1 30%, 2_1 70% |
| 13:56:12 | 132,4 | 26,59 | 26,79 | 1_2 |
| 13:59:07 | 131,4 | 26,39 | 26,64 | 0_2 51%, 1_2 49% |
| 13:59:33 | 129,2 | 25,95 | 26,34 | 0_1 |
| 14:00:08 | 129,2 | 25,95 | 26,33 | 0_1 |
| 14:00:22 | 129,3 | 25,96 | 26,35 | 0_1 |
| 14:00:44 | 129,7 | 26,04 | 26,43 | 0_1 99%, 1_1 1% |
| 14:01:05 | 129,5 | 26,01 | 26,21 | 0_0 |
| 14:01:28 | 134,6 | 27,03 | 26,46 | 2_0 |
| 14:01:53 | 132,9 | 26,70 | 26,59 | 2_1 15%, 2_2 85% |
| 14:02:20 | 132,1 | 26,54 | 26,59 | 1_1 |
| 14:02:36 | 132,3 | 26,57 | 26,62 | 1_1 |
| 14:02:51 | 132,3 | 26,57 | 26,62 | 1_1 |
| 14:03:13 | 132,3 | 26,57 | 26,62 | 1_1 |
| 14:03:22 | 132,3 | 26,57 | 26,62 | 1_1 |
| 14:03:31 | 132,3 | 26,56 | 26,61 | 1_1 |
| 14:03:59 | 132,9 | 26,69 | 26,24 | 1_0 26%, 2_0 74% |
| 14:04:30 | 132,6 | 26,63 | 26,18 | 1_0 26%, 2_0 74% |
| 14:05:24 | 132,3 | 26,58 | 26,77 | 1_2 |
| 14:05:37 | 132,3 | 26,58 | 26,77 | 1_2 |
| 14:06:14 | 132,3 | 26,57 | 26,77 | 1_2 |
| 14:07:01 | 132,3 | 26,58 | 26,78 | 1_2 |
| 14:07:23 | 132,2 | 26,55 | 26,74 | 1_2 |

Circularidade 0,91 a 0,92 em todas as medições: a forma foi bem segmentada.

### Estatísticas (erro = medido − 27,00 mm)

| | Média | Desvio padrão | Amplitude | Viés | Erro médio absoluto | RMSE | Pior erro |
|---|---|---|---|---|---|---|---|
| **Sem correção**, 24 medições | 26,47 | 0,28 | 1,08 | −0,53 | 0,53 | 0,60 | −1,05 |
| **Com correção**, 24 medições | 26,54 | 0,19 | 0,61 | −0,46 | 0,46 | 0,50 | −0,82 |
| **Sem correção**, 1 média por posição (10 posições) | 26,46 | 0,35 | 1,08 | −0,54 | 0,55 | 0,64 | −1,05 |
| **Com correção**, 1 média por posição (10 posições) | 26,47 | 0,19 | 0,56 | −0,53 | 0,53 | 0,56 | −0,79 |

A linha "1 média por posição" é a mais justa: as repetições no mesmo lugar não pesam a mais.

### Tamanho da moeda em pixels conforme a posição

| Linha da grade | Diâmetro (px) | mm/pixel calibrado | mm/pixel que daria 27,00 mm |
|---|---|---|---|
| 0 (topo) | ≈ 129,3 | ≈ 0,203 | ≈ 0,209 (+2,7%) |
| 1 (meio) | ≈ 132,3 | ≈ 0,202 | ≈ 0,204 (+1,0%) |
| 2 (baixo) | ≈ 134,6 | ≈ 0,197 | ≈ 0,201 (+2,0%) |

A moeda varia **4%** em pixels de cima para baixo, mas o tabuleiro variou só **2,4%**. Se os dois estivessem no mesmo plano, essas variações seriam iguais.

## 4. Diagnóstico do viés

| Hipótese | Teste feito | Conclusão |
|---|---|---|
| A segmentação corta a borda da moeda | Perfil de brilho radial nas fotos `_original`: borda a meia altura em r = 65,4 px; contorno segmentado em r = 66,1 px | **Descartada.** O contorno fica 0,7 px *por fora* da borda, ou seja, tenderia a aumentar a moeda, não diminuir. A borda é nítida (transição de ~4 px), então o foco está bom. |
| Espessura da moeda (≈ 2 mm mais perto da câmera) | Conta: 303 / (303 − 2) = +0,7% | **Descartada como causa.** Deixaria a moeda ~0,17 mm *maior*. O viés real é o contrário e ainda maior. |
| **Quadrado impresso diferente de 15,000 mm** | Não dá para testar pelos arquivos | **Possível.** Um quadrado real de ~15,2 a 15,3 mm (impressão em escala > 100%) explicaria um viés de −1% a −2%. **Medir com paquímetro.** |
| **Papel e moeda em planos diferentes** (altura ou inclinação) | Comparação do degradê de pixels (tabela acima) | **Provável.** Se o papel estava ~3 a 6 mm mais alto que a moeda (por exemplo, sobre uma prancheta, ou por cima de um tecido fofo onde a moeda afunda) ou inclinado diferente, a escala fica menor e o degradê diferente, que é o que se vê. |
| Câmera não perpendicular | Degradê linear de cima para baixo nas duas medidas | **Provável, e soma com a anterior.** Não causa viés sozinho se papel e moeda estão no mesmo plano, mas aumenta a variação dentro de cada célula. |
| Valor real da moeda ≠ 27,00 mm | Não medido | Moedas gastas variam alguns centésimos de mm. Não explica 0,5 mm, mas **medir com paquímetro** para usar o valor certo. |

## Próximos passos

**Antes de coletar mais dados** (sem isso, mais amostras só repetem o mesmo viés):

1. **Medir o tabuleiro impresso** com paquímetro ou régua: 10 quadrados devem dar 150,0 mm. Se der outro valor, refazer o `calibrar_escala.bat` com o tamanho medido (ex.: 15,25).
2. **Papel no mesmo plano da moeda:** o papel tem que ficar **diretamente sobre o tecido**, esticado e plano, no lugar dos tomates. Nada de prancheta ou papelão por baixo, a não ser que os objetos também fiquem em cima deles. Se o tecido é fofo, esticar bem ou usar uma base rígida sob o tecido.
3. **Nivelar a câmera:** usar um nível de bolha no celular e no fundo. A linha de baixo não deveria dar 3,6% diferente da linha de cima.
4. **Tabuleiro maior que a região**, sobrando pelo menos 1 quadrado em cada borda. Hoje há só 10 a 12 trechos nas células dos cantos.
5. **Refazer o branco** com mais luz ou exposição (G ≈ 200) e luz difusa. Hoje o vermelho tem ganho de 2,3 e variação de 14,7%.
6. **Medir a moeda** com paquímetro e usar esse valor no `testar_medicao.bat`.
7. Apagar `Bancada/bancada.gain` (calibração antiga).

**Depois disso, coleta para o TCC:**

| Etapa | Quantidade | Observação |
|---|---|---|
| Repetibilidade da escala | 5 calibrações | Reposicionar o tabuleiro a cada vez; reportar mm/px por célula como média ± desvio |
| Moedas no centro de cada célula | 5 moedas × 9 células = 45 | 20 a 27 mm, faixa parecida com tomate cereja. Diâmetro real pelo paquímetro |
| Moedas sobre divisas e cruzamentos | ≈ 10 | Testa o caso de objeto em várias células |
| Repetibilidade da medição | 1 moeda × 10, **tirando e recolocando** a moeda a cada vez | Hoje as repetições foram sem mexer na moeda: isso mede só o ruído da câmera (0,02 mm), não o de posicionamento |
| Tomates (RF04) | 40 a 50 tomates, 2 posições cada | Paquímetro: média de 3 medidas em direções diferentes |

**Meta depois das correções:** viés perto de 0 (|viés| < 0,15 mm), erro médio absoluto < 0,3 mm com moedas, e o "com correção" bem melhor que o "sem correção" em todas as posições.

## Melhorias possíveis no software (ainda não feitas)

- **Registrar as medições em CSV** (hora, posição, células, px, mm sem e com correção, valor real e erro). Hoje os números só ficam escritos na imagem, e esta análise precisou ler as imagens.
- **Escala interpolada** em vez de constante por célula: a escala muda de forma contínua (degradê). Uma superfície suave (interpolação bilinear entre os centros das células, ou homografia do plano) tiraria o "degrau" nas divisas. Só vale fazer depois de nivelar a câmera, porque a inclinação é a principal causa do degradê.
