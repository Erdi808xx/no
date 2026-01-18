@echo off
title No.punq Bot System
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto :Error

:Start
cls
echo --------------------------------------------------
echo No.punq Baslatiliyor...
echo Cikis yapmak icin pencereyi kapatin.
echo --------------------------------------------------
".venv\Scripts\python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot bir hata ile kapandi.
)
echo.
echo Yeniden baslatmak icin bir tusa basin...
pause
goto :Start

:Error
color 4
echo HATA: Sanal ortam (.venv) bulunamadi!
echo Lutfen once kurulumu yapin (python -m venv .venv ve pip install -r requirements.txt)
pause
exit /b
