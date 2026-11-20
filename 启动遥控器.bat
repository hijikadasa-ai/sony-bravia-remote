@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw run_app.py
) else (
    start "" python run_app.py
)
