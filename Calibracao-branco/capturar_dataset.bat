@echo off
rem Captura de fotos de tomates com rotulos de defeito, maturacao e diametro do paquimetro.
rem Pergunta o destino: 1 = defeitos (..\Dataset-proprio), 2 = cor/LUT (..\Dataset-cor),
rem 3 = teste do 2o lote (..\Dataset-teste). Cada pasta tem fotos\ e rotulos.csv (abre no Excel).
rem No terminal: rotulos do tomate. Na janela: ESPACO = foto, ENTER = proximo tomate, ESC = encerrar.
rem Para enviar as fotos ao GitHub depois, rode o enviar.bat.
cd /d "%~dp0"

set "GAIN=bancada.gain"
if not exist "%GAIN%" (
    echo ERRO: "%GAIN%" nao encontrado. Rode o calibrar.bat antes.
    pause
    exit /b 1
)

set "CAMERA=0"
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"camera=" "%GAIN%"') do set "CAMERA=%%B"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [%CAMERA%]: "

echo.
echo Para qual dataset sao as fotos?
echo   1 - defeitos: treino da CNN ^(Dataset-proprio^)
echo   2 - cor: treino da LUT ^(Dataset-cor^). Informe a maturacao de cada tomate.
echo   3 - teste: 2o lote do mercado ^(Dataset-teste^). Nunca usar no treino.
:escolher_destino
set "PASTA="
set "DESTINO="
set /p "DESTINO=Escolha 1, 2 ou 3: "
if "%DESTINO%"=="1" set "PASTA=..\Dataset-proprio"
if "%DESTINO%"=="2" set "PASTA=..\Dataset-cor"
if "%DESTINO%"=="3" set "PASTA=..\Dataset-teste"
if not defined PASTA goto escolher_destino
echo Gravando em: %PASTA%

echo.
echo Dicas:
echo   - Numere fisicamente cada tomate ^(etiqueta ou pote^) com o numero que o programa mostrar.
echo   - Tire 3 ou 4 fotos por tomate, girando o tomate entre elas.
echo   - Mantenha o tomate dentro da area amarela.
echo.

python -m calibracao_branco.labeled_capture_cli --gain "%GAIN%" --camera "%CAMERA%" --pasta "%PASTA%"
if errorlevel 1 (
    echo.
    echo A captura falhou. Leia a mensagem de erro acima.
)
pause
