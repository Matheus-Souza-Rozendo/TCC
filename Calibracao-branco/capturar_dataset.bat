@echo off
rem Captura do dataset proprio: fotos de tomates com rotulos de defeito,
rem maturacao e diametro do paquimetro. Grava em ..\Dataset-proprio\
rem   fotos\tomate_0001_foto_01.jpg ...   e   rotulos.csv (abre no Excel)
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
echo Dicas:
echo   - Numere fisicamente cada tomate ^(etiqueta ou pote^) com o numero que o programa mostrar.
echo   - Tire 3 ou 4 fotos por tomate, girando o tomate entre elas.
echo   - Mantenha o tomate dentro da area amarela.
echo.

python -m calibracao_branco.labeled_capture_cli --gain "%GAIN%" --camera "%CAMERA%"
if errorlevel 1 (
    echo.
    echo A captura falhou. Leia a mensagem de erro acima.
)
pause
