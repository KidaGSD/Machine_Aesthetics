@echo off
SETLOCAL EnableDelayedExpansion

REM Emotion-Driven Parametric Lamp Cover System
REM Windows Batch Script

echo =====================================
echo Emotion-Driven Parametric Lamp Cover System
echo =====================================

REM Get current directory
set SCRIPT_DIR=%~dp0
cd %SCRIPT_DIR%

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python not found in PATH. Please install Python and try again.
    exit /b 1
)

REM Check for audio file argument
if "%~1"=="" (
    echo Usage: %0 path/to/audio.mp3 [options]
    echo.
    echo Options:
    echo   --skip-textures    Skip the texture classification step
    echo   --skip-audio       Skip the audio analysis step
    echo   --skip-blending    Skip the texture blending step
    echo   --skip-design      Skip the parametric design step
    echo   --cpu              Use CPU instead of CUDA
    echo.
    echo Example: %0 my_audio.mp3 --skip-textures
    exit /b 1
)

REM Set variables
set AUDIO_FILE=%~1
set SKIP_TEXTURE_CLASS=0
set SKIP_AUDIO=0
set SKIP_TEXTURES=0
set SKIP_BLENDING=0
set SKIP_DESIGN=0
set DEVICE=cuda

REM Parse arguments
shift
:parse_args
if "%~1"=="" goto end_parse_args
if /i "%~1"=="--skip-textures" set SKIP_TEXTURE_CLASS=1
if /i "%~1"=="--skip-audio" set SKIP_AUDIO=1
if /i "%~1"=="--skip-textures" set SKIP_TEXTURES=1
if /i "%~1"=="--skip-blending" set SKIP_BLENDING=1
if /i "%~1"=="--skip-design" set SKIP_DESIGN=1
if /i "%~1"=="--cpu" set DEVICE=cpu
shift
goto parse_args
:end_parse_args

REM Check if audio file exists
if not exist "%AUDIO_FILE%" (
    echo Audio file not found: %AUDIO_FILE%
    exit /b 1
)

REM Step 1: Texture Classification (if not skipped)
if %SKIP_TEXTURE_CLASS% EQU 0 (
    echo.
    echo Step 1: Texture Classification
    echo =====================================
    python run_workflow.py --confidence 0.4 --device %DEVICE%
    
    if %ERRORLEVEL% NEQ 0 (
        echo Texture classification failed.
        exit /b 1
    )
) else (
    echo Skipping texture classification...
)

REM Prepare command for audio-texture workflow
set CMD=python audio_texture_workflow.py --audio "%AUDIO_FILE%" --device %DEVICE%

REM Add skip options if needed
if %SKIP_AUDIO% EQU 1 set CMD=%CMD% --skip_audio
if %SKIP_TEXTURES% EQU 1 set CMD=%CMD% --skip_textures
if %SKIP_BLENDING% EQU 1 set CMD=%CMD% --skip_blending
if %SKIP_DESIGN% EQU 1 set CMD=%CMD% --skip_design

REM Set textures path
set CMD=%CMD% --textures results/high_confidence_images.txt

REM Run the audio-texture workflow
echo.
echo Running Audio-Texture-Parametric Lamp Design Workflow
echo ===================================================
%CMD%

if %ERRORLEVEL% NEQ 0 (
    echo Workflow execution failed.
    exit /b 1
)

echo.
echo Workflow completed successfully!
echo.
echo Next steps:
echo 1. Open Rhino and load the Grasshopper file (audio_analysis/machine_ase/ghtest01.gh)
echo 2. Import the parameter files from results/parametric_design/
echo 3. Generate the 3D model and export for 3D printing

exit /b 0 