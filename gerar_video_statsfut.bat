@echo off
color 0A
title STATSFUT - Gerador Automatico de Videos IA

echo ========================================================
echo         BEM-VINDO AO MOTOR DE VIDEOS STATSFUT
echo ========================================================
echo.
echo Siga os 3 passos abaixo para gerar seu video sincronizado:
echo.

set /p url="1. Cole a URL da partida (ex: http://127.0.0.1:8000/.../): "
set /p audio="2. Cole o caminho absoluto do arquivo de AUDIO (.mp3/.wav): "
set /p roteiro="3. Cole o caminho absoluto do arquivo do ROTEIRO (.txt): "

echo.
echo ========================================================
echo INICIANDO O PROCESSO DE GRAVACAO E SINCRONIZACAO!
echo ========================================================
echo.
echo [0%%] Carregando ambiente virtual Python...

.\venv\Scripts\python.exe video_maker\gerar_video.py --url "%url%" --audio "%audio%" --roteiro "%roteiro%"

echo.
echo ========================================================
echo [100%%] PROCESSO FINALIZADO! 
echo Se tudo correu bem, o video estara salvo na pasta output!
echo Pressione qualquer tecla para sair...
echo ========================================================
pause > nul
