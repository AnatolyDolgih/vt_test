title script2.bat
@echo on
cd scripts
call .\.venv\Scripts\activate.bat
cd essay_controller
python client.py
