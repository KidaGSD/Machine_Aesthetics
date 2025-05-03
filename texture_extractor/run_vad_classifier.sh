#!/bin/bash

echo "Running VAD-based texture classifier pipeline..."

# Set Python executable - adjust if needed
PYTHON=python3

# Set configuration file
CONFIG=config/vad_pipeline_config.yaml

# Set VAD CSV path - adjust to your actual VAD data file
VAD_CSV=../audio_analysis/machine_ase/luminote/emotion_label.csv

# Set valence bias parameter to improve classification balance
VALENCE_BIAS=0.08

echo "Using valence bias: $VALENCE_BIAS to improve classification balance"

# Run the preprocess_textures.py script with VAD classifier
$PYTHON preprocess_textures.py --config $CONFIG --vad_csv $VAD_CSV --classifier vad --dataset all --valence-bias $VALENCE_BIAS

echo ""
echo "VAD texture classification complete!"
echo "Check the results in the output directory specified in the config file."
echo "" 