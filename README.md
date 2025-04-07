# Emotion-Driven Parametric Lamp Cover System

This project implements a pipeline for generating 3D-printable lamp designs based on the emotional content of audio recordings and textures. It combines audio analysis, texture processing, and parametric design to create unique lamp covers that embody the emotional characteristics of the input.

## System Overview

The pipeline consists of four main components:

1. **Audio Analysis**: Analyzes audio recordings to extract emotion-related features (valence, arousal, dominance).
2. **Texture Processing**: Classifies textures by emotion and selects appropriate textures based on audio emotional content.
3. **Texture Blending**: Creates displacement maps from emotion-driven texture blends.
4. **Parametric Design**: Generates 3D lamp design parameters for Grasshopper/Rhino.

## Installation

### Prerequisites

- Python 3.8+
- CUDA-compatible GPU (recommended)
- [Rhino 7](https://www.rhino3d.com/) with [Grasshopper](https://www.grasshopper3d.com/) (for 3D design)

### Setup

1. Clone this repository
2. Install required Python packages:

```bash
pip install numpy matplotlib pillow opencv-python tqdm pandas scikit-learn torch torchvision librosa transformers
```

3. Download the Describable Textures Dataset:

```bash
python setup_dtd.py
```

## Usage

### Complete Pipeline

To run the entire pipeline from audio to lamp design:

```bash
python audio_texture_workflow.py --audio path/to/audio.mp3 --textures results/high_confidence_images.txt
```

This will:
1. Analyze the audio for emotions
2. Match textures to audio emotion timeline
3. Create blended textures and displacement maps
4. Generate parametric lamp design parameters

### Step-by-Step Usage

If you prefer to run each step separately:

1. **Texture Classification** (if not already done):

```bash
python run_workflow.py --confidence 0.4 --device cuda
```

2. **Audio Analysis**:

```bash
python audio_texture_bridge.py --audio path/to/audio.mp3 --output_dir results/audio_texture
```

3. **Texture Blending**:

```bash
python texture_blender.py --timeline results/audio_texture/texture_timeline.json --output_dir results/blended_textures
```

4. **Parametric Design Generation**:

```bash
python parametric_design_generator.py --data results/blended_textures/animation_data.json --output_dir results/parametric_design
```

### 3D Model Generation

1. Open Rhino and load the Grasshopper file (`audio_analysis/machine_ase/ghtest01.gh`)
2. Import the parameter file from `results/parametric_design/lamp_params_*.json`
3. Generate the 3D model
4. Export for 3D printing

Alternatively, use the generated Rhino Python script:

```bash
# In Rhino Python console:
execfile(r"path/to/results/parametric_design/lamp_params_t_rhino.py")
```

## Command Line Options

### Main Workflow

```
python audio_texture_workflow.py --help
```

Options:
- `--audio`: Path to audio file (required)
- `--textures`: Path to high confidence textures file
- `--emotions`: Path to emotion mapping JSON
- `--output_dir`: Output directory (default: "results/lamp_design")
- `--device`: Device to use (cuda/cpu)
- `--skip_audio`: Skip audio analysis step
- `--skip_textures`: Skip texture selection step
- `--skip_blending`: Skip texture blending step
- `--skip_design`: Skip parametric design step

## File Structure

- `/audio_analysis`: Audio processing and emotion extraction
- `/texture_extractor`: Texture classification and processing
  - `audio_texture_bridge.py`: Maps audio emotions to textures
  - `texture_blender.py`: Blends textures based on emotions
  - `parametric_design_generator.py`: Generates lamp design parameters
  - `audio_texture_workflow.py`: Main workflow script
- `/results`: Output data and visualizations

## Output Structure

The pipeline generates the following outputs:
- Audio emotion timeline (CSV)
- Texture selection timeline (JSON)
- Blended textures and displacement maps (PNG)
- Parametric design parameters (JSON)
- 3D visualization previews (PNG)
- Rhino Python scripts

## Credits

This project combines elements from:
- The Describable Textures Dataset (DTD)
- CLIP model by OpenAI
- Wav2Vec2 for audio emotion extraction
- Rhino/Grasshopper for parametric design 
