@echo off
rem ============================================
rem  PPE CN-literature daily updater + GitHub sync
rem  Called by scheduled task "PPELitDaily"
rem ============================================
cd /d "%~dp0"
set GIT_TERMINAL_PROMPT=0

set PYTHON=C:\Users\Peter\AppData\Local\Python\pythoncore-3.14-64\python.exe
if not exist "%PYTHON%" set PYTHON=python

"%PYTHON%" ppe_nssd_crawler.py --pages 1 >> ppe_cron.log 2>&1
echo [%date% %time%] crawler done >> ppe_cron.log

git add nssd_data.json nssd_data.js
git diff --cached --quiet
if errorlevel 1 goto publish
echo [%date% %time%] no data change, skip push >> ppe_cron.log
goto end

:publish
git commit -m "Update NSSD data" >> ppe_cron.log 2>&1
if errorlevel 1 echo [%date% %time%] git commit FAILED >> ppe_cron.log
git push >> ppe_cron.log 2>&1
if errorlevel 1 (
  echo [%date% %time%] git push FAILED >> ppe_cron.log
) else (
  echo [%date% %time%] pushed to GitHub >> ppe_cron.log
)

:end
exit /b 0
