@echo off
rem Calibra a relacao pixel -> mm por regiao com um tabuleiro de xadrez impresso.
rem Usa a regiao do gabarito branco gravada no .gain e grava a escala no mesmo .gain.
rem Argumentos extras sao repassados ao programa (ex.: calibrar_escala.bat --largura-janela 1280).
cd /d "%~dp0"

set "GAIN=bancada.gain"
set /p "GAIN=Arquivo .gain da calibracao de branco [bancada.gain]: "
if not exist "%GAIN%" (
    echo ERRO: "%GAIN%" nao encontrado. Rode o calibrar.bat antes.
    pause
    exit /b 1
)

set "CAMERA=0"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [0]: "

echo.
echo Cantos INTERNOS = encontros de 4 quadrados. Tabuleiro de 10 x 7 quadrados = 9x6 cantos.
set "CANTOS=9x6"
set /p "CANTOS=Cantos internos do tabuleiro, colunas x linhas [9x6]: "

:pedir_quadrado
set "QUADRADO_MM="
set /p "QUADRADO_MM=Lado de UM quadrado em mm, MEDIDO COM REGUA no papel impresso (ex.: 25 ou 24,8): "
if not defined QUADRADO_MM (
    echo O tamanho do quadrado e obrigatorio: a impressora costuma mudar a escala do papel.
    goto pedir_quadrado
)

set "GRADE=3x3"
set /p "GRADE=Dividir a regiao em quantas celulas, colunas x linhas [3x3]: "

set "SALVAR_FOTO=S"
set /p "SALVAR_FOTO=Salvar foto da deteccao (cantos e celulas)? (S/N) [S]: "
set "FOTO_ARG="
if /i "%SALVAR_FOTO%"=="S" for %%F in ("%GAIN%") do set FOTO_ARG=--foto-deteccao "%%~dpnF_escala.png"
echo.

python -m calibracao_branco.pixel_scale_cli --gain "%GAIN%" --camera "%CAMERA%" --cantos "%CANTOS%" --quadrado-mm "%QUADRADO_MM%" --grade "%GRADE%" %FOTO_ARG% %*
if errorlevel 1 (
    echo.
    echo A calibracao de escala falhou. Leia a mensagem de erro acima.
)
pause
