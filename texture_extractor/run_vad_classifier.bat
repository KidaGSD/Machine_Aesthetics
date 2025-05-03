@echo off
echo Running VAD-based texture classifier pipeline...

REM Set Python executable - adjust if needed
set PYTHON=python

REM Set configuration file
set CONFIG=config/vad_pipeline_config.yaml

REM Set VAD CSV path - using the valence_arousal_timeline-screams.csv which has proper VAD data
set VAD_CSV=../audio_analysis/machine_ase/luminote/valence_arousal_timeline-screams.csv

REM Set valence bias parameter to improve classification balance
set VALENCE_BIAS=0.08

echo Using valence bias: %VALENCE_BIAS% to improve classification balance

REM Run the preprocess_textures.py script with VAD classifier
%PYTHON% preprocess_textures.py --config %CONFIG% --vad_csv %VAD_CSV% --classifier vad --dataset huggingface --valence-bias %VALENCE_BIAS%

echo.
echo VAD texture classification complete!
echo Check the results in the output directory specified in the config file.
echo.

pause 