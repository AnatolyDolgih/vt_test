@echo on
cd scripts
call .\.venv\Scripts\activate.bat
cd ./virtual_tutor/src

python bica_server.py --local