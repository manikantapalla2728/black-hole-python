@echo off
REM Renders the demo to a 1080x1920 MP4:  record.bat out.mp4
if not exist .venv ( py -m venv .venv && .venv\Scripts\pip install -r requirements.txt )
.venv\Scripts\python main.py --record %1 --fps 30
