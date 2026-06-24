@echo off
setlocal

set "ENV_ROOT=C:\Users\akiha\anaconda3\envs\chi-piano"
set "SCRIPT_DIR=%~dp0"

if not exist "%ENV_ROOT%\python.exe" (
    echo Python executable not found: "%ENV_ROOT%\python.exe"
    echo Please check that the chi-piano environment exists.
    pause
    exit /b 1
)

set "PATH=%ENV_ROOT%;%ENV_ROOT%\Library\mingw-w64\bin;%ENV_ROOT%\Library\usr\bin;%ENV_ROOT%\Library\bin;%ENV_ROOT%\Scripts;%PATH%"

cd /d "%SCRIPT_DIR%"
echo Starting Expressive Piano Agent Harness with Gradio...
echo If GRADIO_SERVER_PORT is not set, Gradio will choose an available local port.
echo Check the URL printed below after the server starts.
"%ENV_ROOT%\python.exe" "%SCRIPT_DIR%app.py" %*

if errorlevel 1 (
    echo.
    echo Gradio server exited with an error.
    pause
)

endlocal
