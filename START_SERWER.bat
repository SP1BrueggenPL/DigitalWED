@echo off
title WED Digital Platform
cd /d C:\DigitalWED
echo.
echo  ==========================================
echo   H. ^& J. Bruggen KG - WED Digital Platform
echo  ==========================================
echo.
echo  Uruchamianie serwera...
echo  Otworz przegladarke: http://localhost:8000
echo.
start "" http://localhost:8000
python manage.py runserver 8000
pause
