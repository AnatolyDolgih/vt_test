@echo on
REM ========================================================
REM run_all.bat — Launch four scripts in separate windows
REM ========================================================

cd scripts
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install uvicorn FastAPI pydantic requests 
from contextlib import asynccontextmanager

cd ..
cd Windows
start "Script 5" cmd /c "Classroom_actual.exe"

cd ..
cd scripts

cd ZoomDemo
python plug.py
pause

exit