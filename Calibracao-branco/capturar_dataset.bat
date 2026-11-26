@echo off
rem Abre a janela de captura de fotos de tomates com rotulos.
rem Na janela: escolha o destino (Cor, Defeitos ou Teste), marque os rotulos e clique em
rem "Tirar foto" (ou barra de espaco). As pastas sao criadas sozinhas, separadas por classe:
rem   ..\Dataset-cor\fotos\imaturo, intermediario, maduro
rem   ..\Dataset-proprio\fotos\sadio, com_defeito
rem   ..\Dataset-teste\fotos
rem Cada pasta de dataset tem tambem o rotulos.csv (abre no Excel).
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
echo Abrindo a janela de captura...

python -m calibracao_branco.capture_gui --gain "%GAIN%" --camera "%CAMERA%" --raiz ".."
if errorlevel 1 (
    echo.
    echo A captura falhou. Leia a mensagem de erro acima.
    pause
)
