@echo off
rem Gera a LUT de cor (MLP) a partir das fotos de ..\Dataset-cor (capturar_dataset.bat, destino Cor).
rem 1. Segmenta os tomates e agrupa os pixels por cor.
rem 2. Abre um painel com os grupos: voce diz o que e cada grupo (verde, amarelado, rosado, vermelho, calice).
rem 3. Treina a MLP, gera lut_cor.npz e confere a maturacao de cada foto.
rem Resultado: lut_cor.npz, ..\Dataset-cor\lut\RELATORIO.md e ..\Dataset-cor\lut\conferencia\
cd /d "%~dp0"

if not exist "bancada.gain" (
    echo ERRO: "bancada.gain" nao encontrado. Rode o calibrar.bat antes.
    goto fim
)
if not exist "..\Dataset-cor\rotulos.csv" (
    echo ERRO: sem fotos em ..\Dataset-cor. Rode o capturar_dataset.bat com o destino Cor.
    goto fim
)

set "REAGRUPAR_ARG="
if not exist "..\Dataset-cor\lut\grupos.json" goto gerar
set "REAGRUPAR=N"
set /p "REAGRUPAR=Ja existem nomes de grupos salvos. Refazer os grupos e nomear de novo? (S/N) [N]: "
if /i "%REAGRUPAR%"=="S" set "REAGRUPAR_ARG=--reagrupar"

:gerar
python -m calibracao_branco.lut_cli --gain bancada.gain --pasta "..\Dataset-cor" --saida lut_cor.npz %REAGRUPAR_ARG%
if errorlevel 1 (
    echo.
    echo A geracao da LUT falhou. Leia a mensagem de erro acima.
)
:fim
pause
