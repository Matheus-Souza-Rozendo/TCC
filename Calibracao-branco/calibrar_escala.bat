@echo off
rem Calibra a relacao pixel -> mm por regiao com um tabuleiro de xadrez impresso.
rem Pergunta a camera e o tamanho do quadrado. O resto e automatico:
rem   - regiao de interesse: lida do .gain (gravada pelo calibrar.bat)
rem   - camera: pergunta, sugerindo a gravada no .gain
rem   - numero de cantos do tabuleiro: detectado na imagem
rem   - resultado: gravado no mesmo .gain + foto <nome>_escala.png
rem Para usar outro .gain, arraste o arquivo em cima deste .bat.
cd /d "%~dp0"

set "GAIN=bancada.gain"
if not "%~1"=="" set "GAIN=%~1"
if not exist "%GAIN%" (
    echo ERRO: "%GAIN%" nao encontrado. Rode o calibrar.bat antes.
    pause
    exit /b 1
)
echo Usando: %GAIN%
echo.

set "CAMERA=0"
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"camera=" "%GAIN%"') do set "CAMERA=%%B"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [%CAMERA%]: "

:pedir_quadrado
set "QUADRADO_MM="
set /p "QUADRADO_MM=Lado de UM quadrado em mm, MEDIDO COM REGUA no papel impresso (ex.: 25 ou 24,8): "
if not defined QUADRADO_MM (
    echo O tamanho do quadrado e obrigatorio: a impressora costuma mudar a escala do papel.
    goto pedir_quadrado
)
echo.

for %%F in ("%GAIN%") do set "FOTO=%%~dpnF_escala.png"
python -m calibracao_branco.pixel_scale_cli --gain "%GAIN%" --camera "%CAMERA%" --quadrado-mm "%QUADRADO_MM%" --foto-deteccao "%FOTO%"
if errorlevel 1 (
    echo.
    echo A calibracao de escala falhou. Leia a mensagem de erro acima.
)
pause
