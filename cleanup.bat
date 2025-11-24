@echo off
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

:: Delete all .log files from \scripts\virtual_tutor\logs_moral\4
if exist "scripts\virtual_tutor\logs_moral\4\*.log" (
    echo Deleting .log files from scripts\virtual_tutor\logs_moral\4...
    del "scripts\virtual_tutor\logs_moral\4\*.log" /q
) else (
    echo No .log files found in scripts\virtual_tutor\logs_moral\4
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

echo Cleanup completed!
pause