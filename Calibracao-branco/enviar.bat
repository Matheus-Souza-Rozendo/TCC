@echo off
rem Envia para o GitHub tudo o que mudou neste PC (ex.: bancada.gain, fotos, medicoes).
rem Faz: git add de tudo, commit com a mensagem digitada, fetch + rebase e push.
rem Se um envio anterior falhou (sem internet, por exemplo), o commit que ficou
rem guardado neste PC e enviado junto.
setlocal
cd /d "%~dp0.."

where git >nul 2>nul
if errorlevel 1 (
    echo ERRO: Git nao encontrado. Instale em https://git-scm.com
    goto fim_com_erro
)

for /f "delims=" %%N in ('git config user.name') do set "GIT_NOME=%%N"
if not defined GIT_NOME (
    echo ERRO: o Git deste PC nao sabe quem voce e. Rode uma vez:
    echo   git config --global user.name "Seu Nome"
    echo   git config --global user.email "seu@email.com"
    goto fim_com_erro
)

set "MUDANCAS="
for /f "delims=" %%L in ('git status --porcelain') do set "MUDANCAS=1"
set "PENDENTES=0"
for /f %%C in ('git rev-list --count "@{u}..HEAD"') do set "PENDENTES=%%C"

if defined MUDANCAS goto criar_commit
if "%PENDENTES%"=="0" (
    echo Nada mudou desde o ultimo envio. Nada para enviar.
    goto fim
)
echo Nenhum arquivo novo, mas ha %PENDENTES% commit^(s^) de um envio anterior que nao subiu.
goto enviar

:criar_commit
echo Arquivos que serao enviados. Para cancelar, feche esta janela agora:
git status --short
echo.
set "MENSAGEM=Resultados da bancada"
set /p "MENSAGEM=Descricao do envio [Resultados da bancada]: "
git add -A
git commit -q -m "%MENSAGEM%"
if errorlevel 1 (
    echo ERRO: nao foi possivel criar o commit.
    goto fim_com_erro
)

:enviar
rem Puxa antes de enviar: se o outro PC mandou alteracoes, o push seria recusado.
rem Baixar e encaixar ficam separados para a mensagem de erro dizer a causa certa.
git fetch -q
if errorlevel 1 (
    echo.
    echo ERRO: nao foi possivel falar com o GitHub. Confira a internet e o login.
    echo O seu commit foi mantido aqui; rode este .bat de novo depois.
    goto fim_com_erro
)

git rebase -q "@{u}"
if errorlevel 1 (
    git rebase --abort >nul 2>nul
    echo.
    echo ERRO: as alteracoes deste PC conflitam com as do GitHub.
    echo O seu commit foi mantido aqui, nada foi perdido. Peca ajuda para resolver o conflito.
    goto fim_com_erro
)

git push -q
if errorlevel 1 (
    echo.
    echo ERRO: o envio falhou. Confira a internet e o login do GitHub.
    echo Na primeira vez o Git abre uma janela pedindo para entrar na conta do GitHub.
    goto fim_com_erro
)

echo.
echo Enviado com sucesso.
goto fim

:fim_com_erro
echo.
echo O envio NAO foi feito.
:fim
pause
