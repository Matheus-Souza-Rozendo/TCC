@echo off
rem Puxa as ultimas alteracoes do GitHub para esta pasta.
cd /d "%~dp0.."

where git >nul 2>nul
if errorlevel 1 (
    echo ERRO: Git nao encontrado. Instale em https://git-scm.com
    pause
    exit /b 1
)

git pull --ff-only
if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel atualizar. Se voce alterou arquivos neste PC,
    echo salve-os em outro lugar e rode "git checkout -- ." antes de tentar de novo.
    pause
    exit /b 1
)

echo.
echo Projeto atualizado.
pause
