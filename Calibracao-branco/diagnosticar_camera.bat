@echo off
rem Testa os indices de camera 0 a 5 e, opcionalmente, a URL do DroidCam por Wi-Fi.
cd /d "%~dp0"
set "OPENCV_LOG_LEVEL=FATAL"

set "URL="
set /p "URL=URL do DroidCam por Wi-Fi (ex.: http://192.168.0.10:4747/video) ou ENTER para testar so a USB/indices: "

if defined URL (
    python -m calibracao_branco.diagnostico 0 1 2 3 4 5 "%URL%"
) else (
    python -m calibracao_branco.diagnostico
)
pause
