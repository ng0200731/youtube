@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt -q
start http://localhost:5000
py tools/server.py
pause
