@echo off
rem Abre a calibracao de branco. Argumentos extras sao repassados ao programa
rem (ex.: calibrar.bat --estrategia nivel_alvo --regiao 200,150,240,180).
cd /d "%~dp0"

set "CAMERA=0"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [0]: "

set "SAIDA=bancada.gain"
set /p "SAIDA=Arquivo de saida [bancada.gain]: "

python -m calibracao_branco --camera "%CAMERA%" --saida "%SAIDA%" %*
if errorlevel 1 (
    echo.
    echo A calibracao falhou. Leia a mensagem de erro acima.
)
pause
