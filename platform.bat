@echo on
REM ========================================================
REM run_all.bat — Launch four scripts in separate windows
REM ========================================================

cd scripts
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
REM if something's missing, run python -m pip wheel -w ./wheelhouse -r cor_requirements.txt 
python -m pip install --no-index --find-links ./wheelhouse -r cor_requirements.txt 

call .venv\Scripts\deactivate.bat
cd ..

for /f "delims=" %%i in ('powershell -Command "Start-Process 'script1.bat' -PassThru | Select-Object -ExpandProperty Id"') do set PID1=%%i
echo Process 1 started with PID: %PID1%
for /f "delims=" %%i in ('powershell -Command "Start-Process 'script2.bat' -PassThru | Select-Object -ExpandProperty Id"') do set PID2=%%i
echo Process 2 started with PID: %PID2%
for /f "delims=" %%i in ('powershell -Command "Start-Process 'script3.bat' -PassThru | Select-Object -ExpandProperty Id"') do set PID3=%%i
echo Process 3 started with PID: %PID3%
for /f "delims=" %%i in ('powershell -Command "Start-Process 'script4.bat' -PassThru | Select-Object -ExpandProperty Id"') do set PID4=%%i
echo Process 4 started with PID: %PID4%
for /f "delims=" %%i in ('powershell -Command "Start-Process 'script6.bat' -PassThru | Select-Object -ExpandProperty Id"') do set PID6=%%i
echo Process 6 started with PID: %PID6%

echo %PID1% %PID2% %PID3% %PID4% %PID6%>> test.txt

cd Windows 

REM 5) Script 5
start "Script 5" cmd /c "Classroom_actual.exe"
timeout /t 5 /nobreak >nul

:MONITOR
timeout /t 1 /nobreak >nul
tasklist /fi "imagename eq Classroom_actual.exe" | find "Classroom_actual.exe" >nul
if errorlevel 1 goto SHUTDOWN
goto MONITOR

:SHUTDOWN
cd ..
echo Script 5 finished.
echo Cleaning up files...

:: Delete all .wav files from \scripts\ZoomDemo\recordings
if exist "scripts\ZoomDemo\recordings\*.wav" (
    echo Deleting .wav files from scripts\ZoomDemo\recordings...
    del "scripts\ZoomDemo\recordings\*.wav" /q
) else (
    echo No .wav files found in scripts\ZoomDemo\recordings
)

:: Delete all .wav files from \scripts\virtual_tutor\src
if exist "scripts\virtual_tutor\src\*.wav" (
    echo Deleting .wav files from scripts\virtual_tutor\src...
    del "scripts\virtual_tutor\src\*.wav" /q
) else (
    echo No .wav files found in scripts\virtual_tutor\src
)

:: Delete all .log files from \scripts\essay_controller\logs\client
if exist "scripts\essay_controller\logs\client\*.log" (
    echo Deleting .log files from scripts\essay_controller\logs\client...
    del "scripts\essay_controller\logs\client\*.log" /q
) else (
    echo No .log files found in scripts\essay_controller\logs\client
)

:: Delete all .log files from \scripts\ZoomDemo
if exist "scripts\ZoomDemo\*.log" (
    echo Deleting .log files from scripts\ZoomDemo...
    del "scripts\ZoomDemo\*.log" /q
) else (
    echo No .log files found in scripts\ZoomDemo
)

:: Delete all .log files from Convai
if exist "Windows\Classroom_actual\ConvaiLog\*.log" (
    echo Deleting .log files from Windows\Classroom_actual\ConvaiLog...
    del "Windows\Classroom_actual\ConvaiLog\*.log" /q
) else (
    echo No .log files found in Windows\Classroom_actual\ConvaiLog
)

del test.txt

echo Cleanup completed!
echo Shutting down all script windows...

taskkill /F /T /PID %PID1%
taskkill /F /T /PID %PID2%
taskkill /F /T /PID %PID3%
taskkill /F /T /PID %PID4%
taskkill /F /T /PID %PID6%
exit