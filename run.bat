@echo off
REM Interactive experiment (add --demo to start the scripted sequence)
if not exist .venv ( py -m venv .venv && .venv\Scripts\pip install -r requirements.txt )
.venv\Scripts\python main.py %*
