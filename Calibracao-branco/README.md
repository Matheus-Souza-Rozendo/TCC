# Calibração da bancada

Duas calibrações, gravadas no mesmo arquivo `.gain`:

1. **Branco** (`calibrar.bat`): mede o gabarito branco e calcula o ganho de cada canal (R, G, B).
2. **Escala pixel → mm** (`calibrar_escala.bat`): mede um tabuleiro de xadrez **só na região do gabarito** e calcula quantos mm vale 1 pixel em cada parte dessa região.

Rode sempre nessa ordem: a escala usa a região gravada pela calibração de branco.

## Atalhos (.bat)

| Arquivo | O que faz |
|---|---|
| `instalar.bat` | Instala as dependências (rode uma vez) |
| `calibrar.bat` | Pergunta a câmera, o arquivo de saída, a estratégia de ganho (1 = `referencia_verde`, 2 = `nivel_alvo`) e se salva a foto antes × depois; depois abre a calibração |
| `calibrar_escala.bat` | Pergunta o `.gain`, a câmera, os cantos internos do tabuleiro, o lado do quadrado em mm, a grade de células e se salva a foto da detecção; grava a escala no mesmo `.gain` |
| `atualizar.bat` | Puxa as últimas alterações do GitHub (`git pull`) |
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
python -m calibracao_branco.pixel_scale_cli --gain bancada.gain --camera 1 --cantos 9x6 --quadrado-mm 24.8 --grade 3x3
```

**Antes de rodar:**
1. Imprima um tabuleiro de xadrez **sem ajustar à página** e **meça um quadrado com régua**: a impressora costuma mudar a escala.
2. Cole o papel numa superfície plana e coloque **na altura onde ficam os tomates**, sobre o tecido.
3. O tabuleiro precisa cobrir **toda a região amarela** (a região do gabarito branco), com sobra, e aparecer **inteiro** na imagem.

**Como funciona:**
1. Lê a `regiao_gabarito` do `.gain` e mostra essa região em amarelo na câmera ao vivo. Posicione o tabuleiro e aperte **ENTER**.
2. Faz a média de 10 quadros e encontra os cantos internos com precisão subpixel.
3. Divide a região em células (padrão 3x3). Em cada célula, mede em pixels a distância entre cantos vizinhos, que vale 1 quadrado em mm.
   Isso compensa a distorção da lente: nas bordas, o mesmo tamanho em mm ocupa menos pixels.
4. Calcula o erro de cada célula (diferença entre o quadrado medido com a escala e o tamanho real) e compara com **0,5 mm (RF05)**.
5. Grava a escala no `.gain` e mostra a imagem: **verde** = dentro de 0,5 mm, **vermelho** = fora.

| Opção | Padrão | Uso |
|---|---|---|
| `--gain` | `bancada.gain` | Arquivo de onde vem a região e onde a escala é gravada |
| `--camera` | `0` | Índice da webcam ou URL |
| `--cantos` | `9x6` | Cantos **internos** (colunas x linhas). Tabuleiro de 10 x 7 quadrados = 9x6 |
| `--quadrado-mm` | (obrigatório) | Lado de um quadrado em mm, medido com régua. Aceita vírgula |
| `--grade` | `3x3` | Em quantas células dividir a região (colunas x linhas) |
| `--foto-deteccao` | (não salva) | Salva a imagem com cantos e células. O `.bat` salva como `<nome do .gain>_escala.png` |
| `--largura-janela` | `960` | Largura das janelas na tela |
| `--sem-conferencia` | | Não abre a janela no final |

O programa **para com erro** se não achar o tabuleiro, ou se alguma célula tiver menos de 4 trechos do tabuleiro (tabuleiro não cobre a região).
Nesse caso, use quadrados menores ou uma grade com menos células.

**Se refizer a calibração de branco:** com a mesma região, a escala é mantida. Com outra região, a escala antiga é apagada (ela deixa de valer) e o programa avisa para rodar o `calibrar_escala.bat` de novo.

## Formato do `.gain`

```text
# Ganhos de balanço de branco por canal
data=2026-11-26T10:30:00
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
escala_tabuleiro_cantos_internos=9x6
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
| `chessboard.py` | `ChessboardPattern` e `ChessboardDetector` (cantos internos com subpixel) |
| `pixel_scale.py` | Grade de células da região, cálculo de mm/pixel e erro por célula, `PixelScaleMap` |
| `scale_file.py` | Grava/lê a seção de escala no `.gain` e a tolerância do RF05 |
| `scale_overlay.py` | Desenho da região, dos cantos e das células; `RegionOverlayFrameSourceDecorator` (Decorator) |
| `pixel_scale_cli.py` | Linha de comando da calibração de escala |
| `comparison.py` / `image_files.py` | Foto antes × depois e gravação de imagens |
