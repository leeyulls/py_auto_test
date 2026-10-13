@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

cd /d "d:\py_auto_test"
echo [Daily Briefing Task Started: %DATE% %TIME%] >> "reports\daily_run.log"

"C:\Users\jjht7\AppData\Local\Programs\Python\Python312\python.exe" "d:\py_auto_test\main.py" >> "reports\daily_run.log" 2>&1

echo [Daily Briefing Task Finished: %DATE% %TIME%] >> "reports\daily_run.log"
