import os
import sys
import argparse
import json
from pathlib import Path
import time
import pandas as pd
import numpy as np

# Add the current directory to the path to ensure imports work
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import the modules we created
from audio_texture_bridge import AudioTextureMapper
from texture_blender import TextureBlender
from parametric_design_generator import ParametricDesignGenerator

def create_directory_structure(base_dir):
    """Create the necessary directory structure for the workflow."""
    # Main output directories
    dirs = [
        os.path.join(base_dir, "audio_analysis"),
        os.path.join(base_dir, "texture_timeline"),
        os.path.join(base_dir, "blended_textures"),
        os.path.join(base_dir, "parametric_design")
    ]
    
    # Create directories
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    
    return dirs

def run_audio_analysis(audio_file, output_dir, device="cuda"):
    """Run audio analysis to extract emotions."""
    print("\n" + "="*80)
    print("Step 1: Audio Analysis and Emotion Extraction")
    print("="*80)
    
    # Create mapper instance
    mapper = AudioTextureMapper(device=device)
    
    # Process audio file
    print(f"Processing audio file: {audio_file}")
    timeline = mapper.process_audio_file(audio_file, output_dir)
    
    print(f"Audio analysis complete. Results saved to {output_dir}")
    
    return timeline

def run_texture_selection(audio_timeline_path, texture_paths_file, output_dir, emotion_mapping=None):
    """Select textures based on audio emotions."""
    print("\n" + "="*80)
    print("Step 2: Texture Selection Based on Emotions")
    print("="*80)
    
    # Create mapper instance
    mapper = AudioTextureMapper(
        audio_timeline_path=audio_timeline_path,
        high_confidence_textures_path=texture_paths_file,
        emotion_mapping_path=emotion_mapping
    )
    
    # Generate texture timeline
    texture_timeline_path = os.path.join(output_dir, "texture_timeline.json")
    texture_timeline = mapper.generate_texture_timeline(texture_timeline_path)
    
    # Visualize timeline
    viz_path = os.path.join(output_dir, "emotion_texture_timeline.png")
    mapper.visualize_timeline(texture_timeline, viz_path)
    
    print(f"Texture selection complete. Timeline saved to {texture_timeline_path}")
    
    return texture_timeline_path

def run_texture_blending(texture_timeline_path, output_dir):
    """Blend textures and create displacement maps."""
    print("\n" + "="*80)
    print("Step 3: Texture Blending and Displacement Map Generation")
    print("="*80)
    
    # Create blender instance
    blender = TextureBlender(texture_timeline_path, output_dir)
    
    # Process timeline
    results = blender.process_timeline()
    
    # Create summary visualization
    summary_path = os.path.join(output_dir, "summary_visualization.png")
    blender.create_summary_visualization(results, summary_path)
    
    # Create animation data
    animation_path = os.path.join(output_dir, "animation_data.json")
    blender.create_animation_data(results, animation_path)
    
    print(f"Texture blending complete. Results saved to {output_dir}")
    print(f"Animation data saved to {animation_path}")
    
    return animation_path

def run_parametric_design(animation_data_path, output_dir):
    """Generate parametric design parameters for lamp."""
    print("\n" + "="*80)
    print("Step 4: Parametric Lamp Design Generation")
    print("="*80)
    
    # Create generator instance
    generator = ParametricDesignGenerator(animation_data_path, output_dir)
    
    # Process all time points
    results = generator.process_time_points()
    
    # Generate Rhino script for first result
    if results:
        param_path = results[0]["parameters_path"]
        script_path = param_path.replace(".json", "_rhino.py")
        generator.generate_rhino_python_script(param_path, script_path)
    
    print(f"Parametric design generation complete. Results saved to {output_dir}")
    
    return results

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Audio-Texture-Parametric Lamp Design Workflow")
    parser.add_argument("--audio", type=str, required=True, help="Path to audio file")
    parser.add_argument("--textures", type=str, help="Path to high confidence textures file (from run_workflow.py)")
    parser.add_argument("--emotions", type=str, help="Path to emotion mapping JSON")
    parser.add_argument("--output_dir", type=str, default="results/lamp_design", help="Output directory")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use (cuda/cpu)")
    parser.add_argument("--skip_audio", action="store_true", help="Skip audio analysis step")
    parser.add_argument("--skip_textures", action="store_true", help="Skip texture selection step")
    parser.add_argument("--skip_blending", action="store_true", help="Skip texture blending step")
    parser.add_argument("--skip_design", action="store_true", help="Skip parametric design step")
    args = parser.parse_args()
    
    # Check if audio file exists
    if not os.path.exists(args.audio):
        print(f"Error: Audio file {args.audio} not found.")
        return 1
    
    # Create output directory structure
    output_dir = args.output_dir
    audio_dir, texture_dir, blending_dir, design_dir = create_directory_structure(output_dir)
    
    # Check for texture paths file
    texture_paths_file = args.textures
    if not texture_paths_file or not os.path.exists(texture_paths_file):
        # Try to use default path
        default_path = os.path.join(script_dir, "results", "high_confidence_images.txt")
        if os.path.exists(default_path):
            texture_paths_file = default_path
            print(f"Using default texture paths file: {texture_paths_file}")
        else:
            print("Warning: No texture paths file provided. Please run texture classification first.")
            print("You can use run_workflow.py to classify textures and generate high_confidence_images.txt")
            return 1
    
    # Record start time
    start_time = time.time()
    
    # Step 1: Audio Analysis
    if not args.skip_audio:
        try:
            audio_timeline = run_audio_analysis(args.audio, audio_dir, args.device)
            audio_timeline_path = os.path.join(audio_dir, "audio_emotion_timeline.csv")
        except Exception as e:
            print(f"Error in audio analysis: {e}")
            print("Creating synthetic audio timeline for testing...")
            # Create a synthetic timeline
            synthetic_timeline = []
            for i in range(20):  # 20 time points
                synthetic_timeline.append({
                    "Start Time (s)": i * 5.0,
                    "Valence": 0.5 + (np.random.random() - 0.5) * 0.4,
                    "Arousal": 0.5 + (np.random.random() - 0.5) * 0.4,
                    "Dominance": 0.5
                })
            
            timeline_df = pd.DataFrame(synthetic_timeline)
            audio_timeline_path = os.path.join(audio_dir, "audio_emotion_timeline.csv")
            timeline_df.to_csv(audio_timeline_path, index=False)
            print(f"Created synthetic timeline at {audio_timeline_path}")
    else:
        # Look for existing audio timeline
        audio_timeline_path = os.path.join(audio_dir, "audio_emotion_timeline.csv")
        if not os.path.exists(audio_timeline_path):
            print(f"Error: Audio timeline not found at {audio_timeline_path}")
            print("Please run audio analysis first or provide a valid audio timeline.")
            return 1
        print(f"Skipping audio analysis, using existing timeline: {audio_timeline_path}")
    
    # Step 2: Texture Selection
    if not args.skip_textures:
        texture_timeline_path = run_texture_selection(
            audio_timeline_path, 
            texture_paths_file, 
            texture_dir,
            args.emotions
        )
    else:
        # Look for existing texture timeline
        texture_timeline_path = os.path.join(texture_dir, "texture_timeline.json")
        if not os.path.exists(texture_timeline_path):
            print(f"Error: Texture timeline not found at {texture_timeline_path}")
            print("Please run texture selection first or provide a valid texture timeline.")
            return 1
        print(f"Skipping texture selection, using existing timeline: {texture_timeline_path}")
    
    # Step 3: Texture Blending
    if not args.skip_blending:
        animation_data_path = run_texture_blending(texture_timeline_path, blending_dir)
    else:
        # Look for existing animation data
        animation_data_path = os.path.join(blending_dir, "animation_data.json")
        if not os.path.exists(animation_data_path):
            print(f"Error: Animation data not found at {animation_data_path}")
            print("Please run texture blending first or provide valid animation data.")
            return 1
        print(f"Skipping texture blending, using existing animation data: {animation_data_path}")
    
    # Step 4: Parametric Design
    if not args.skip_design:
        design_results = run_parametric_design(animation_data_path, design_dir)
    else:
        print("Skipping parametric design generation.")
    
    # Calculate and display execution time
    execution_time = time.time() - start_time
    print("\n" + "="*80)
    print(f"Workflow completed in {execution_time:.2f} seconds")
    print(f"All results saved to {output_dir}")
    print("="*80)
    
    # Print summary of outputs
    print("\nSummary of generated files:")
    print(f"- Audio emotion timeline: {audio_timeline_path}")
    print(f"- Texture timeline: {texture_timeline_path}")
    print(f"- Animation data: {animation_data_path}")
    print(f"- Parametric design files: {design_dir}")
    print("\nNext steps:")
    print("1. Open the Rhino/Grasshopper files in the parametric_design directory")
    print("2. Load the parameter files to generate 3D lamp models")
    print("3. Export models for 3D printing")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 