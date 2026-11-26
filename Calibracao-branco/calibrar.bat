@echo off
rem Abre a calibracao de branco. Argumentos extras sao repassados ao programa
rem (ex.: calibrar.bat --regiao 200,150,240,180 --largura-janela 1280).
cd /d "%~dp0"

set "CAMERA=0"
set /p "CAMERA=Indice da camera do DroidCam (0, 1, 2...) ou URL http://IP:4747/video [0]: "

set "SAIDA=bancada.gain"
set /p "SAIDA=Arquivo de saida [bancada.gain]: "

:escolher_estrategia
echo.
echo Estrategia de calculo do ganho:
echo   1 - referencia_verde : verde fica com ganho 1; so corrige a cor, nao muda o brilho
echo   2 - nivel_alvo       : leva o branco a 230 nos tres canais; corrige cor e brilho
set "OPCAO=1"
set /p "OPCAO=Escolha 1 ou 2 [1]: "

if "%OPCAO%"=="1" (
    set "ESTRATEGIA=referencia_verde"
) else if "%OPCAO%"=="2" (
    set "ESTRATEGIA=nivel_alvo"
) else (
    echo Opcao invalida: "%OPCAO%". Digite 1 ou 2.
    goto escolher_estrategia
)
echo Usando: %ESTRATEGIA%
echo.

set "SALVAR_FOTO=S"
set /p "SALVAR_FOTO=Salvar foto de comparacao antes x depois? (S/N) [S]: "
set "FOTO_ARG="
if /i "%SALVAR_FOTO%"=="S" for %%F in ("%SAIDA%") do set FOTO_ARG=--foto-comparacao "%%~dpnF_comparacao.png"
echo.

python -m calibracao_branco --camera "%CAMERA%" --saida "%SAIDA%" --estrategia %ESTRATEGIA% %FOTO_ARG% %*
if errorlevel 1 (
    echo.
    echo A calibracao falhou. Leia a mensagem de erro acima.
)
pause
