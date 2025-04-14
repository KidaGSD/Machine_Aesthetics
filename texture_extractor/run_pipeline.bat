@echo off
SETLOCAL EnableDelayedExpansion

REM Runs the Emotion-Driven Parametric Lamp Cover System Pipeline
REM Uses main.py and configuration from config/pipeline_config.yaml

echo ===================================================
echo Emotion-Driven Parametric Lamp Cover System Pipeline
echo ===================================================

REM Get current directory (where the script is located)
set SCRIPT_DIR=%~dp0
cd /D "%SCRIPT_DIR%"

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python not found in PATH. Please install Python and add it to PATH.
    exit /b 1
)

REM --- Configuration ---
set CONFIG_FILE=config\pipeline_config.yaml
set PYTHON_EXE=python

REM --- Argument Parsing ---
set SKIP_MAPPING=
set SKIP_BLENDING=
set SKIP_DESIGN=
set EXTRA_ARGS=

:parse_args
if "%~1"=="" goto end_parse_args
if /i "%~1"=="--skip_mapping" set SKIP_MAPPING=--skip_mapping
if /i "%~1"=="--skip_blending" set SKIP_BLENDING=--skip_blending
if /i "%~1"=="--skip_design" set SKIP_DESIGN=--skip_design
REM Add other potential overrides here, e.g., --config
REM if /i "%~1"=="--config" (
REM     set CONFIG_FILE=%~2
REM     shift
REM )
shift
goto parse_args
:end_parse_args

REM Check if config file exists
if not exist "%CONFIG_FILE%" (
    echo Configuration file not found: %CONFIG_FILE%
    exit /b 1
)

REM --- Execute Main Pipeline Script ---
echo.
echo Running main pipeline script (main.py)...
echo Using config: %CONFIG_FILE%
echo Skip args: %SKIP_MAPPING% %SKIP_BLENDING% %SKIP_DESIGN%
echo.

%PYTHON_EXE% main.py --config "%CONFIG_FILE%" %SKIP_MAPPING% %SKIP_BLENDING% %SKIP_DESIGN%

set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% NEQ 0 (
    echo.
    echo Pipeline execution failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo.
echo Pipeline completed successfully!
echo Review results in the 'results' directory.

exit /b 0
