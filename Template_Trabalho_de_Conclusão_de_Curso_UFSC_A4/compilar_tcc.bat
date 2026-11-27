@echo off
rem Recompila o TCC (pdflatex + biber + pdflatex) e gera o main.pdf nesta pasta.
rem Usa o TinyTeX instalado em %LOCALAPPDATA%\TinyTeX-dl.
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\TinyTeX-dl\TinyTeX\bin\windows;%PATH%"

where latexmk >nul 2>nul
if errorlevel 1 (
    echo ERRO: TinyTeX nao encontrado em %LOCALAPPDATA%\TinyTeX-dl.
    goto fim
)

echo Compilando o TCC...
latexmk -g -pdf -interaction=nonstopmode -silent main.tex
if errorlevel 1 (
    echo.
    echo A compilacao falhou. Veja os erros no main.log ^(linhas que comecam com "!"^).
    findstr /b /c:"!" main.log
    goto fim
)

echo.
echo Pronto: main.pdf atualizado.
:fim
pause
