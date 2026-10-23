@echo off
rem ============================================
rem  PPE CN-literature daily updater
rem  Called by scheduled task "PPELitDaily"
rem ============================================
cd /d "%~dp0"

set PYTHON=C:\Users\Peter\AppData\Local\Python\pythoncore-3.14-64\python.exe

if not exist "%PYTHON%" set PYTHON=python

"%PYTHON%" ppe_nssd_crawler.py --pages 1 >> ppe_cron.log 2>&1
echo [%date% %time%] crawler done >> ppe_cron.log
