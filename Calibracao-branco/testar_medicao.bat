@echo off
rem Teste de medicao: segmenta objetos claros sobre o fundo preto e mede o diametro
rem sem correcao (uma escala so) e com a correcao por regiao do bancada.gain.
rem Resultado: medicoes\medicao_<data_hora>.png (+ _original.png quando usa a camera).
rem Para medir uma imagem salva em vez da camera, arraste a imagem em cima deste .bat.
cd /d "%~dp0"

set "GAIN=bancada.gain"
if not exist "%GAIN%" (
    echo ERRO: "%GAIN%" nao encontrado. Rode o calibrar.bat e o calibrar_escala.bat antes.
    pause
    exit /b 1
)

set "ORIGEM_ARG="
if not "%~1"=="" (
    echo Medindo a imagem: %~1
    set ORIGEM_ARG=--imagem "%~1"
    goto pedir_diametro
)

set "CAMERA=0"
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"camera=" "%GAIN%"') do set "CAMERA=%%B"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [%CAMERA%]: "
set ORIGEM_ARG=--camera "%CAMERA%"

:pedir_diametro
echo.
echo Diametro real do objeto, para calcular o erro. Moedas do Real:
echo   5 centavos = 22 mm ^| 10 centavos = 20 mm ^| 25 centavos = 25 mm ^| 50 centavos = 23 mm ^| 1 real = 27 mm
set "DIAMETRO="
set /p "DIAMETRO=Diametro real em mm (ENTER = nao informar): "
echo.

python -m calibracao_branco.measurement_cli --gain "%GAIN%" %ORIGEM_ARG% --diametro-real-mm "%DIAMETRO%"
if errorlevel 1 (
    echo.
    echo A medicao falhou. Leia a mensagem de erro acima.
)
pause
