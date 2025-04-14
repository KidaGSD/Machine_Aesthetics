#!/bin/bash

# Runs the Emotion-Driven Parametric Lamp Cover System Pipeline
# Uses main.py and configuration from config/pipeline_config.yaml

echo "==================================================="
echo "Emotion-Driven Parametric Lamp Cover System Pipeline"
echo "==================================================="

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1 # Exit if cd fails

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3 and ensure it's in your PATH."
    exit 1
fi

# --- Configuration ---
CONFIG_FILE="config/pipeline_config.yaml"
PYTHON_EXE="python3"

# --- Argument Parsing ---
SKIP_MAPPING_ARG=""
SKIP_BLENDING_ARG=""
SKIP_DESIGN_ARG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --skip_mapping)
            SKIP_MAPPING_ARG="--skip_mapping"
            ;;
        --skip_blending)
            SKIP_BLENDING_ARG="--skip_blending"
            ;;
        --skip_design)
            SKIP_DESIGN_ARG="--skip_design"
            ;;
        --config)
            shift
            CONFIG_FILE="$1"
            ;;
        *)
            echo "Unknown option: $1"
            # Optionally show usage here
            exit 1
            ;;
    esac
    shift
done

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# --- Execute Main Pipeline Script ---
echo ""
echo "Running main pipeline script (main.py)..."
echo "Using config: $CONFIG_FILE"
echo "Skip args: $SKIP_MAPPING_ARG $SKIP_BLENDING_ARG $SKIP_DESIGN_ARG"
echo ""

# Construct command
CMD="$PYTHON_EXE main.py --config \"$CONFIG_FILE\" $SKIP_MAPPING_ARG $SKIP_BLENDING_ARG $SKIP_DESIGN_ARG"

# Execute the command
eval $CMD
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Pipeline execution failed with exit code $EXIT_CODE."
    exit $EXIT_CODE
fi

echo ""
echo "Pipeline completed successfully!"
echo "Review results in the 'results' directory."

exit 0
