@echo off
rem Avalia a LUT e a CNN no lote de teste (..\Dataset-teste): tomates que nenhum modelo viu.
rem Rode uma vez so, com os modelos prontos. Resultado: ..\Dataset-teste\avaliacao\RELATORIO.md
cd /d "%~dp0"
python -m calibracao_branco.holdout_evaluation_cli --gain bancada.gain --pasta "..\Dataset-teste" --lut lut_cor.npz --cnn cnn_defeito.onnx
pause
