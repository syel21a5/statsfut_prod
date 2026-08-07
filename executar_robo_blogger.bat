@echo off
echo ========================================================
echo   Robo StatsFut - Postagens Individuais no Blogger
echo ========================================================
echo Iniciando a criacao e agendamento dos posts...

:: Navega para o diretorio do projeto
cd /d "i:\GitHub\statsfut\statsfut"

:: Ativa o ambiente virtual Python
call venv\Scripts\activate

:: Executa o comando Django que gera os posts
python manage.py post_jogos_individuais

echo ========================================================
echo   Processo Finalizado com Sucesso!
echo ========================================================
pause
