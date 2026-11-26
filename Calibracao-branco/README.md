# Calibração da bancada

Duas calibrações, gravadas no mesmo arquivo `.gain`:

1. **Branco** (`calibrar.bat`): mede o gabarito branco e calcula o ganho de cada canal (R, G, B).
2. **Escala pixel → mm** (`calibrar_escala.bat`): mede um tabuleiro de xadrez **só na região do gabarito** e calcula quantos mm vale 1 pixel em cada parte dessa região.

Rode sempre nessa ordem: a escala usa a região gravada pela calibração de branco.

Depois, o `testar_medicao.bat` mede objetos circulares (ex.: moeda) para conferir as duas calibrações.

## Atalhos (.bat)

| Arquivo | O que faz |
|---|---|
| `instalar.bat` | Instala as dependências (rode uma vez) |
| `calibrar.bat` | Pergunta a câmera, o arquivo de saída, a estratégia de ganho (1 = `referencia_verde`, 2 = `nivel_alvo`) e se salva a foto antes × depois; depois abre a calibração |
| `calibrar_escala.bat` | Pergunta a **câmera** (sugere a gravada no `.gain`; ENTER aceita) e o **lado do quadrado em mm**. A região vem do `bancada.gain` e os cantos são detectados sozinhos; grava a escala no mesmo `.gain` e salva `bancada_escala.png`. Para outro `.gain`, arraste o arquivo em cima do `.bat` |
| `testar_medicao.bat` | Captura pela câmera (ou mede uma imagem arrastada em cima do `.bat`), segmenta objetos claros sobre o fundo preto e mede o diâmetro sem e com a correção por região. Pergunta o diâmetro real (opcional) para mostrar o erro. Salva em `medicoes\` |
| `capturar_dataset.bat` | Fotos do dataset próprio com rótulos: para cada tomate pergunta defeitos, maturação e diâmetro do paquímetro; ESPAÇO tira foto. Grava em `..\Dataset-proprio\` |
| `atualizar.bat` | Puxa as últimas alterações do GitHub (`git pull`) |
| `enviar.bat` | Envia ao GitHub tudo o que mudou neste PC (ex.: `bancada.gain`, fotos, `medicoes\`). Mostra os arquivos, pede uma descrição, baixa o que o outro PC enviou antes e faz o push. Se faltar internet, o commit fica guardado e sobe no próximo envio |
| `diagnosticar_camera.bat` | Testa os índices 0 a 5 (e a URL do Wi-Fi, se informada) e mostra quais entregam imagem |

## Instalação (no PC da bancada)

```bash
pip install -r requirements.txt
```

## Câmera não abre (DroidCam)

1. Rode `diagnosticar_camera.bat` e use no `calibrar.bat` um índice ou URL que mostre `OK`.
2. **USB/índice:** o cliente DroidCam do PC precisa estar aberto e **conectado**, com vídeo aparecendo nele.
   Desconectado, a webcam virtual mostra só a imagem de espera do DroidCam. O diagnóstico diz `OK`, mas a imagem não é a da câmera.
3. **Wi-Fi/URL:** PC e celular na mesma rede. Teste a URL `http://IP:4747/video` no navegador primeiro.
   Feche o cliente do PC: o app do celular aceita uma conexão por vez.
4. Feche outros programas que usam câmera (Teams, navegador, OBS).

O programa tenta sozinho os backends DirectShow, Media Foundation e automático, e fica com o primeiro que entrega imagem.

## Antes de rodar

1. Monte a iluminação e coloque o gabarito branco na posição dos tomates.
2. No app DroidCam, **trave o balanço de branco e a exposição**, se o app permitir.
   Se a câmera continuar no automático, ela muda as cores sozinha e o ganho perde a validade.
3. Feche a caixa escura.

## Como rodar

```bash
python -m calibracao_branco --camera 1 --saida bancada.gain
```

1. Abre a câmera ao vivo. Posicione o gabarito e aperte **ENTER**.
2. Arraste um retângulo **só sobre o branco** e aperte **ENTER**.
3. O programa descarta 15 quadros (estabilização), faz a média de 30 e grava o `.gain`.
4. Abre a comparação original × corrigido. Aperte **ESC** para sair.

| Opção | Padrão | Uso |
|---|---|---|
| `--camera` | `0` | Índice da webcam do DroidCam (teste 0, 1, 2) ou URL `http://IP:4747/video` |
| `--saida` | `calibracao.gain` | Arquivo gerado |
| `--estrategia` | `referencia_verde` | `referencia_verde`: só corrige a cor. `nivel_alvo`: leva o branco a 230 (cor e brilho) |
| `--regiao` | (mouse) | Região fixa `x,y,largura,altura`. Use o valor `regiao_gabarito` do último `.gain` para repetir a mesma região |
| `--quadros` | `30` | Quadros na média |
| `--largura-janela` | `960` | Largura das janelas na tela; a altura segue a proporção. Só muda a exibição: a medição usa a resolução original |
| `--foto-comparacao` | (não salva) | Salva uma foto antes × depois, na resolução original, no caminho `.png`/`.jpg` informado. O `calibrar.bat` salva como `<nome do .gain>_comparacao.png` |
| `--sem-conferencia` | | Não abre a janela de comparação no final |

O programa **para com erro** se o gabarito estiver estourado (≥ 250) ou escuro demais (< 60).
Se o branco não for uniforme (variação > 8%), ele grava o arquivo com um `# AVISO`.

## Calibração de escala pixel → mm

```bash
python -m calibracao_branco.pixel_scale_cli --gain bancada.gain --quadrado-mm 24.8
```

**Antes de rodar:**
1. Imprima um tabuleiro de xadrez **sem ajustar à página** e **meça um quadrado com régua**: a impressora costuma mudar a escala.
2. Cole o papel numa superfície plana e coloque **na altura onde ficam os tomates**, sobre o tecido.
3. O tabuleiro precisa cobrir **toda a região amarela** (a região do gabarito branco), com sobra.
   Ele **não** precisa aparecer inteiro: pode sair pela borda da imagem, e o número de cantos é detectado sozinho.

**Como funciona:**
1. Lê a `regiao_gabarito` do `.gain` e mostra essa região em amarelo na câmera ao vivo. Posicione o tabuleiro e aperte **ENTER**.
2. Faz a média de 10 quadros e encontra os cantos internos com precisão subpixel, sem precisar saber quantos são.
3. Divide a região em células (padrão 3x3). Em cada célula, mede em pixels a distância entre cantos vizinhos, que vale 1 quadrado em mm.
   Isso compensa a distorção da lente: nas bordas, o mesmo tamanho em mm ocupa menos pixels.
4. Calcula o erro de cada célula (diferença entre o quadrado medido com a escala e o tamanho real) e compara com **0,5 mm (RF05)**.
5. Grava a escala no `.gain` e mostra a imagem: **verde** = dentro de 0,5 mm, **vermelho** = fora.

| Opção | Padrão | Uso |
|---|---|---|
| `--gain` | `bancada.gain` | Arquivo de onde vem a região e onde a escala é gravada |
| `--camera` | (a do `.gain`) | Índice da webcam ou URL. Sem ela, usa a câmera gravada pelo `calibrar.bat` |
| `--quadrado-mm` | (obrigatório) | Lado de um quadrado em mm, medido com régua. Aceita vírgula |
| `--grade` | `3x3` | Em quantas células dividir a região (colunas x linhas) |
| `--foto-deteccao` | (não salva) | Salva a imagem com cantos e células. O `.bat` salva como `<nome do .gain>_escala.png` |
| `--largura-janela` | `960` | Largura das janelas na tela |
| `--sem-conferencia` | | Não abre a janela no final |

O programa **para com erro** se não achar o tabuleiro (precisam aparecer pelo menos 4 x 4 quadrados), ou se alguma célula tiver menos de 4 trechos do tabuleiro (tabuleiro não cobre a região).
Nesse caso, use quadrados menores ou uma grade com menos células.

**Se refizer a calibração de branco:** com a mesma região, a escala é mantida. Com outra região, a escala antiga é apagada (ela deixa de valer) e o programa avisa para rodar o `calibrar_escala.bat` de novo.

## Teste de medição

```bash
python -m calibracao_branco.measurement_cli --gain bancada.gain --diametro-real-mm 27
python -m calibracao_branco.measurement_cli --imagem medicoes/medicao_20261126_140000_original.png
```

**Como funciona:**
1. Captura a imagem (média de 5 quadros) com a região de interesse em amarelo, ou lê a imagem de `--imagem`.
2. Aplica os ganhos do branco.
3. **Segmenta** só dentro da região: objeto claro sobre fundo preto, com limiar automático (Otsu), limpeza morfológica e buracos internos preenchidos (reflexo escuro na moeda não reduz a área). Exige contraste mínimo com o fundo, para não medir manchas do tecido.
4. **Diâmetro sem correção:** diâmetro do círculo de mesma área, em pixels × mm/pixel médio da região (uma escala só).
5. **Diâmetro com correção por região:** cada pixel do objeto vale `(mm/pixel da célula dele)²` em mm². A soma dá a área real, e dela sai o diâmetro.
   Por isso o objeto pode cair em **uma ou mais células**: cada parte usa a escala da sua célula. A imagem mostra quanto do objeto ficou em cada célula.
6. Salva `medicoes\medicao_<data_hora>.png` com o contorno, o círculo equivalente e os tamanhos.
   Quando captura pela câmera, salva também `_original.png`. Assim dá para repetir a medição depois com `--imagem` (os ganhos são aplicados de novo).

O programa **para com erro** se não achar objeto claro, ou se algum objeto encostar na borda da região (seria medido cortado).
Se o objeto não for redondo (circularidade < 0,85), a imagem avisa `NAO circular`.

| Opção | Padrão | Uso |
|---|---|---|
| `--gain` | `bancada.gain` | Precisa ter as duas calibrações |
| `--camera` | (a do `.gain`) | Índice ou URL |
| `--imagem` | (câmera) | Mede uma imagem salva em vez de capturar |
| `--diametro-real-mm` | (não informa) | Diâmetro real para calcular o erro. Moedas: 5¢ = 22, 10¢ = 20, 25¢ = 25, 50¢ = 23, R$ 1 = 27 mm |
| `--pasta-saida` | `medicoes` | Pasta das imagens de resultado |
| `--largura-janela` | `960` | Largura das janelas na tela |
| `--sem-conferencia` | | Não abre a janela com o resultado |

## Captura do dataset próprio

```bash
python -m calibracao_branco.labeled_capture_cli --gain bancada.gain
```

Para cada tomate:
1. **No terminal**, os rótulos:
   - **defeitos**: letras juntas, em qualquer ordem: `r` = rachado, `p` = podre, `d` = dano mecânico, `m` = mancha (ex.: `rp`). ENTER = sadio. `sair` encerra a sessão;
   - **maturação** (opcional): `1` = imaturo, `2` = intermediário, `3` = maduro;
   - **diâmetro no paquímetro** em mm (opcional; aceita vírgula).
2. **Na janela da câmera**: ESPAÇO tira uma foto (gire o tomate entre as fotos), ENTER passa para o próximo tomate, ESC encerra.

O número do tomate é automático (continua do último do CSV). Numere fisicamente cada tomate com esse número, para conferir depois.

Saída em `../Dataset-proprio/` (vai para o GitHub pelo `enviar.bat`):
- `fotos/tomate_0001_foto_01.jpg`: imagem limpa da câmera (média de 3 quadros, sem a marcação amarela, sem o ganho do branco aplicado), JPG qualidade 95;
- `rotulos.csv`: uma linha por foto, com `;` e vírgula decimal (abre direto no Excel). Colunas: `arquivo; tomate; foto; data_hora; rachado; podre; dano_mecanico; mancha; sadio; maturacao; diametro_paquimetro_mm`. Cada defeito é 0 ou 1 (multirrótulo); `sadio` = 1 quando não há nenhum defeito.

**Divisão train/val/test: sempre por tomate**, usando a coluna `tomate`. Fotos do mesmo tomate em conjuntos diferentes vazam informação para o teste.

## Formato do `.gain`

```text
# Ganhos de balanço de branco por canal
data=2026-11-26T10:30:00
camera=1
estrategia=referencia_verde
quadros_media=30
regiao_gabarito=200,150,240,180
media_r=171.204
media_g=182.551
media_b=196.880
variacao_r=0.0213
variacao_g=0.0198
variacao_b=0.0220
ganho_r=1.066277
ganho_g=1.000000
ganho_b=0.927219
```

Depois do `calibrar_escala.bat`, o arquivo ganha a seção de escala:

```text
# ===== Escala pixel -> mm por região =====
escala_data=2026-11-26T11:00:00
escala_regiao_interesse=200,150,240,180
escala_grade=3x3
escala_cantos_detectados=9x6
escala_tamanho_quadrado_mm=24.800
escala_mm_por_pixel_medio=0.412300
escala_erro_max_mm=0.1800
escala_tolerancia_mm=0.5
celula_0_0_regiao=200,150,80,60
celula_0_0_mm_por_pixel=0.413100
celula_0_0_trechos=14
celula_0_0_erro_max_mm=0.1500
celula_0_0_erro_medio_mm=0.0600
...
```

Células: `celula_<linha>_<coluna>`, contando a partir de 0 no canto superior esquerdo.
Linhas com `#` são comentários. Cada linha é `chave=valor`.

## Como usar o ganho no resto do projeto

```python
from pathlib import Path
from calibracao_branco import GainFileReader, apply_gains

gains = GainFileReader().read_gains(Path("bancada.gain"))
corrected_frame = apply_gains(frame_bgr, gains)
```

## Como usar a escala no resto do projeto

```python
from pathlib import Path
from calibracao_branco import ScaleSectionReader

scale_map = ScaleSectionReader().read(Path("bancada.gain"))
diameter_mm = diameter_px * scale_map.mm_per_pixel_at(center_x, center_y)
```

`mm_per_pixel_at` dá erro se o ponto estiver fora da região calibrada.

## Como medir no resto do projeto

```python
from pathlib import Path
from calibracao_branco import (CircularObjectMeasurer, DarkBackgroundSegmenter, GainFileReader,
                               ScaleSectionReader, apply_gains)

gain_file = Path("bancada.gain")
scale_map = ScaleSectionReader().read(gain_file)
frame = apply_gains(frame_bgr, GainFileReader().read_gains(gain_file))
measurer = CircularObjectMeasurer(scale_map)
for segment in DarkBackgroundSegmenter().segment(frame, scale_map.grid.region):
    print(measurer.measure(segment).diameter_mm_region_corrected)
```

## Testes

```bash
python -m unittest discover -s tests -t .
```

## Estrutura

| Módulo | Responsabilidade |
|---|---|
| `camera.py` | `OpenCvCameraAdapter`: isola o OpenCV (índice ou URL do DroidCam) |
| `region.py` | Região do gabarito na imagem |
| `sampling.py` | Média de vários quadros e validação (estouro, escuro, uniformidade) |
| `gain_strategies.py` | Regras de cálculo do ganho (Strategy) e `GainStrategyFactory` |
| `calibrator.py` | Junta medição e regra de ganho |
| `gain_file.py` | Grava/lê o `.gain` e aplica o ganho na imagem |
| `preview.py` | Janelas do OpenCV (separadas da lógica) |
| `cli.py` | Linha de comando da calibração de branco |
| `calibration_sections.py` | Divide o `.gain` nas seções de branco e de escala; cada calibração reescreve só a sua |
| `key_value_file.py` | Leitura e gravação do formato `chave=valor` |
| `chessboard.py` | `ChessboardDetector`: acha o tabuleiro sem saber o número de cantos, aceita tabuleiro cortado pela borda |
| `pixel_scale.py` | Grade de células da região, cálculo de mm/pixel e erro por célula, `PixelScaleMap` |
| `scale_file.py` | Grava/lê a seção de escala no `.gain` e a tolerância do RF05 |
| `scale_overlay.py` | Desenho da região, dos cantos e das células; `RegionOverlayFrameSourceDecorator` (Decorator) |
| `pixel_scale_cli.py` | Linha de comando da calibração de escala |
| `comparison.py` / `image_files.py` | Foto antes × depois; leitura e gravação de imagens (aceitam acento no caminho) |
| `drawing.py` | Retângulos e caixas de texto proporcionais à resolução |
| `segmentation.py` | `ObjectSegmenter` (interface) e `DarkBackgroundSegmenter`: objetos claros sobre fundo preto |
| `object_measurement.py` | `CircularObjectMeasurer`: diâmetro em px, sem correção e com correção por região, circularidade |
| `measurement_overlay.py` | Imagem de resultado da medição |
| `measurement_cli.py` | Linha de comando do teste de medição |
| `labeled_capture.py` | Rótulos do dataset próprio, nomes das fotos e o `rotulos.csv` |
| `labeled_capture_cli.py` | Linha de comando da captura rotulada (`TomatoPhotoSession`) |
