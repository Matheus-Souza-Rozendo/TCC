@echo off
rem Treina a CNN de defeitos (sadio x com defeito) com as fotos de ..\Dataset-proprio.
rem 1. Validacao cruzada por tomate (5 dobras): estima o desempenho em tomates novos.
rem 2. Modelo final com todos os tomates: cnn_defeito.onnx (usado pelo classificar.bat).
rem Resultado: ..\Dataset-proprio\cnn\RELATORIO.md, curvas de aprendizado e recortes errados.
rem Precisa do PyTorch (pesado). Use de preferencia um PC com placa de video NVIDIA.
cd /d "%~dp0"

if not exist "bancada.gain" (
    echo ERRO: "bancada.gain" nao encontrado. Rode o calibrar.bat antes.
    goto fim
)
if not exist "..\Dataset-proprio\rotulos.csv" (
    echo ERRO: sem fotos em ..\Dataset-proprio. Rode o capturar_dataset.bat com o destino Defeitos.
    goto fim
)

python -c "import torch, torchvision, onnx" >nul 2>nul
if errorlevel 1 (
    echo PyTorch nao encontrado. Instalando requirements-treino.txt ^(pode demorar^)...
    python -m pip install -r requirements-treino.txt
    if errorlevel 1 goto fim
)

python -m calibracao_branco.defect_training_cli --gain bancada.gain --pasta "..\Dataset-proprio" --saida cnn_defeito.onnx
if errorlevel 1 (
    echo.
    echo O treino falhou. Leia a mensagem de erro acima.
)
:fim
pause
