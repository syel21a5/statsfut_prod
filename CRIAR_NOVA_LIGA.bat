@echo off
title StatsFut - Gerador de Ligas
echo ==================================================
echo   BEM VINDO AO GERADOR AUTOMATICO DE LIGAS
echo ==================================================
echo.
cd /d %~dp0

set PYTHON_EXEC=python
if exist venv\Scripts\python.exe (
    set PYTHON_EXEC=venv\Scripts\python.exe
)

%PYTHON_EXEC% gerador_de_ligas.py

echo.
echo ==================================================
echo   CONCLUIDO!
echo ==================================================
pause
