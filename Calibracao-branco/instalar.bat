@echo off
rem Instala as dependencias Python da calibracao de branco.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale em https://www.python.org e marque "Add Python to PATH".
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: falha ao instalar as dependencias.
    pause
    exit /b 1
)

echo.
echo Dependencias instaladas com sucesso.
pause
