@echo off
rem Abre a IHM de classificacao: maturacao (LUT), defeito (CNN) e tamanho (mm) de cada tomate.
rem Na janela: "Classificar" (ou barra de espaco) tira a foto e classifica; C liga a classificacao
rem continua no video; Esc volta ao video ao vivo.
rem Cada tomate classificado vai para inspecoes\inspecoes_AAAA-MM-DD.csv (abre no Excel).
rem Precisa de: bancada.gain (calibrar.bat + calibrar_escala.bat), lut_cor.npz (gerar_lut.bat)
rem e cnn_defeito.onnx (treinar_cnn.bat). Sem a LUT ou a CNN a janela abre assim mesmo e avisa.
cd /d "%~dp0"

set "GAIN=bancada.gain"
if not exist "%GAIN%" (
    echo ERRO: "%GAIN%" nao encontrado. Rode o calibrar.bat e o calibrar_escala.bat antes.
    pause
    exit /b 1
)

set "CAMERA=0"
for /f "tokens=1,* delims==" %%A in ('findstr /b /c:"camera=" "%GAIN%"') do set "CAMERA=%%B"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [%CAMERA%]: "
echo Abrindo a IHM de classificacao...

python -m calibracao_branco.inspection_gui --gain "%GAIN%" --camera "%CAMERA%" --lut lut_cor.npz --cnn cnn_defeito.onnx --pasta-registro inspecoes
if errorlevel 1 (
    echo.
    echo A IHM falhou. Leia a mensagem de erro acima.
    pause
)
