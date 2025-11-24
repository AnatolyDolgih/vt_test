title script6.bat
@echo on
cd scripts
call .\.venv\Scripts\activate.bat
cd essay_controller
python client_2.py
