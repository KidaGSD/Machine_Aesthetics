#!/bin/bash

# Emotion-Driven Parametric Lamp Cover System
# Unix/Mac Shell Script

echo "====================================="
echo "Emotion-Driven Parametric Lamp Cover System"
echo "====================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3 and try again."
    exit 1
fi

# Check for audio file argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 path/to/audio.mp3 [options]"
    echo ""
    echo "Options:"
    echo "  --skip-textures    Skip the texture classification step"
    echo "  --skip-audio       Skip the audio analysis step"
    echo "  --skip-blending    Skip the texture blending step"
    echo "  --skip-design      Skip the parametric design step"
    echo "  --cpu              Use CPU instead of CUDA"
    echo ""
    echo "Example: $0 my_audio.mp3 --skip-textures"
    exit 1
fi

# Set variables
AUDIO_FILE="$1"
SKIP_TEXTURE_CLASS=0
SKIP_AUDIO=0
SKIP_TEXTURES=0
SKIP_BLENDING=0
SKIP_DESIGN=0
DEVICE="cuda"

# Parse arguments
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --skip-textures)
            SKIP_TEXTURE_CLASS=1
            SKIP_TEXTURES=1
            ;;
        --skip-audio)
            SKIP_AUDIO=1
            ;;
        --skip-blending)
            SKIP_BLENDING=1
            ;;
        --skip-design)
            SKIP_DESIGN=1
            ;;
        --cpu)
            DEVICE="cpu"
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done

# Check if audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
    echo "Audio file not found: $AUDIO_FILE"
    exit 1
fi

# Step 1: Texture Classification (if not skipped)
if [ $SKIP_TEXTURE_CLASS -eq 0 ]; then
    echo ""
    echo "Step 1: Texture Classification"
    echo "====================================="
    python3 run_workflow.py --confidence 0.4 --device $DEVICE
    
    if [ $? -ne 0 ]; then
        echo "Texture classification failed."
        exit 1
    fi
else
    echo "Skipping texture classification..."
fi

# Prepare command for audio-texture workflow
CMD="python3 audio_texture_workflow.py --audio \"$AUDIO_FILE\" --device $DEVICE"

# Add skip options if needed
if [ $SKIP_AUDIO -eq 1 ]; then
    CMD="$CMD --skip_audio"
fi
if [ $SKIP_TEXTURES -eq 1 ]; then
    CMD="$CMD --skip_textures"
fi
if [ $SKIP_BLENDING -eq 1 ]; then
    CMD="$CMD --skip_blending"
fi
if [ $SKIP_DESIGN -eq 1 ]; then
    CMD="$CMD --skip_design"
fi

# Set textures path
CMD="$CMD --textures results/high_confidence_images.txt"

# Run the audio-texture workflow
echo ""
echo "Running Audio-Texture-Parametric Lamp Design Workflow"
echo "==================================================="
eval $CMD

if [ $? -ne 0 ]; then
    echo "Workflow execution failed."
    exit 1
fi

echo ""
echo "Workflow completed successfully!"
echo ""
echo "Next steps:"
echo "1. Open Rhino and load the Grasshopper file (audio_analysis/machine_ase/ghtest01.gh)"
echo "2. Import the parameter files from results/parametric_design/"
echo "3. Generate the 3D model and export for 3D printing"

exit 0 