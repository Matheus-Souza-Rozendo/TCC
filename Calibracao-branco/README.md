# Calibração de branco

Mede o gabarito branco pela câmera (DroidCam) e gera um arquivo `.gain` com o ganho de cada canal (R, G, B).

## Atalhos (.bat)

| Arquivo | O que faz |
|---|---|
| `instalar.bat` | Instala as dependências (rode uma vez) |
| `calibrar.bat` | Pergunta a câmera, o arquivo de saída e a estratégia de ganho (1 = `referencia_verde`, 2 = `nivel_alvo`) e abre a calibração |
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
| `--sem-conferencia` | | Não abre a janela de comparação no final |

O programa **para com erro** se o gabarito estiver estourado (≥ 250) ou escuro demais (< 60).
Se o branco não for uniforme (variação > 8%), ele grava o arquivo com um `# AVISO`.

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

Linhas com `#` são comentários. Cada linha é `chave=valor`.

## Como usar o ganho no resto do projeto

```python
from pathlib import Path
from calibracao_branco import GainFileReader, apply_gains

gains = GainFileReader().read_gains(Path("bancada.gain"))
corrected_frame = apply_gains(frame_bgr, gains)
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
| `cli.py` | Linha de comando |
