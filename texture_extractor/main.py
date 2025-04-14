import os
import sys
import argparse
import json
import time
import yaml  # For loading YAML config
from pathlib import Path

# Ensure the src directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Import the refactored modules from src
try:
    from texture_mapper import AudioTextureMapper # Renamed from audio_texture_bridge
    from texture_blender import TextureBlender
    from parametric_generator import ParametricDesignGenerator # Renamed from parametric_design_generator
    # Import evaluation module if needed later
    # from evaluation_module import PipelineEvaluator
    # Import utilities for dataset detection 
    from utils import detect_dataset_type, is_normal_map_available
except ImportError as e:
    print(f"Error importing modules from src: {e}")
    print(f"Please ensure __init__.py exists in {src_dir} and all module files are present.")
    sys.exit(1)

def load_config(config_path):
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        print(f"Error loading configuration file {config_path}: {e}")
        sys.exit(1)

def resolve_paths(config, base_dir):
    """Resolve relative paths in the config against a base directory."""
    resolved_config = config.copy()
    
    # Determine the results base directory based on dataset type
    dataset_type = resolved_config.get('dataset_preference', 'all')
    if dataset_type == 'huggingface':
        results_base = os.path.join(base_dir, resolved_config.get('hugging_results_dir', 'hugging_results'))
    else:
        results_base = os.path.join(base_dir, config.get('results_base_dir', 'results'))
    
    # Resolve input paths
    if 'original_textures_dir' in resolved_config and not os.path.isabs(resolved_config['original_textures_dir']):
        resolved_config['original_textures_dir'] = os.path.join(base_dir, resolved_config['original_textures_dir'])
    if 'audio_timeline_path' in resolved_config and not os.path.isabs(resolved_config['audio_timeline_path']):
        resolved_config['audio_timeline_path'] = os.path.join(base_dir, resolved_config['audio_timeline_path'])
    if 'emotion_mapping_path' in resolved_config and not os.path.isabs(resolved_config['emotion_mapping_path']):
        resolved_config['emotion_mapping_path'] = os.path.join(base_dir, resolved_config['emotion_mapping_path'])
    # Add VAD CSV path resolution
    if 'vad_csv_path' in resolved_config and not os.path.isabs(resolved_config['vad_csv_path']):
        resolved_config['vad_csv_path'] = os.path.join(base_dir, resolved_config['vad_csv_path'])

    # Resolve output paths relative to results_base
    resolved_config['results_base_dir'] = results_base # Store absolute base results path
    
    for key, suffix in [
        ('classification_output_dir', 'classification'),
        ('depth_maps_output_dir', 'depth_maps'),
        ('timeline_output_dir', 'timeline'),
        ('blending_output_dir', 'blending'),
        ('parametric_output_dir', 'parametric'),
        ('evaluation_output_dir', 'evaluation')
    ]:
        resolved_config[key] = os.path.join(results_base, config.get(key, suffix))

    # Resolve specific output filenames within their directories
    cls_conf = resolved_config.get('classification', {})
    if 'high_confidence_list_filename' in cls_conf:
        cls_conf['high_confidence_list_path'] = os.path.join(resolved_config['classification_output_dir'], cls_conf['high_confidence_list_filename'])
    if 'classification_results_filename' in cls_conf:
         cls_conf['classification_results_path'] = os.path.join(resolved_config['classification_output_dir'], cls_conf['classification_results_filename'])
    resolved_config['classification'] = cls_conf # Update sub-dict

    map_conf = resolved_config.get('texture_mapping', {})
    if 'texture_timeline_filename' in map_conf:
        map_conf['texture_timeline_path'] = os.path.join(resolved_config['timeline_output_dir'], map_conf['texture_timeline_filename'])
    resolved_config['texture_mapping'] = map_conf

    blend_conf = resolved_config.get('texture_blending', {})
    if 'animation_data_filename' in blend_conf:
        blend_conf['animation_data_path'] = os.path.join(resolved_config['blending_output_dir'], blend_conf['animation_data_filename'])
    if 'blending_results_filename' in blend_conf:
         blend_conf['blending_results_path'] = os.path.join(resolved_config['blending_output_dir'], blend_conf['blending_results_filename'])
    resolved_config['texture_blending'] = blend_conf

    design_conf = resolved_config.get('parametric_design', {})
    if 'design_results_filename' in design_conf:
        design_conf['design_results_path'] = os.path.join(resolved_config['parametric_output_dir'], design_conf['design_results_filename'])
    resolved_config['parametric_design'] = design_conf
        
    return resolved_config

def ensure_directories(config):
    """Create necessary output directories defined in the config."""
    print("Ensuring output directories exist...")
    dirs_to_create = [
        config['results_base_dir'],
        config['classification_output_dir'],
        config['depth_maps_output_dir'],
        config['timeline_output_dir'],
        config['blending_output_dir'],
        config['parametric_output_dir'],
        config['evaluation_output_dir']
    ]
    for d in dirs_to_create:
        try:
            os.makedirs(d, exist_ok=True)
            # print(f"  - Ensured: {d}")
        except Exception as e:
            print(f"Error creating directory {d}: {e}")
            sys.exit(1)
    print("Output directories checked/created.")


# --- Pipeline Stages ---

def run_texture_mapping(config):
    """Select textures based on audio emotions."""
    print("\n" + "="*80)
    print("Stage 1: Texture Mapping (Audio Timeline -> Texture Timeline)")
    print("="*80)
    
    map_config = config.get('texture_mapping', {})
    cls_config = config.get('classification', {})
    
    audio_timeline_path = config.get('audio_timeline_path')
    high_conf_path = cls_config.get('high_confidence_list_path')
    emotion_map_path = config.get('emotion_mapping_path')
    output_timeline_path = map_config.get('texture_timeline_path')
    output_dir = config.get('timeline_output_dir') # For visualization
    device = config.get('device') # Pass device if needed by mapper internals (though audio analysis removed)

    # Input validation
    if not audio_timeline_path or not os.path.exists(audio_timeline_path):
        print(f"Error: Audio timeline path not found or not specified in config: {audio_timeline_path}")
        return None
    if not high_conf_path or not os.path.exists(high_conf_path):
        print(f"Error: High confidence texture list not found or not specified in config: {high_conf_path}")
        print("Please run texture preprocessing (preprocess_textures.py) first.")
        return None
    if not output_timeline_path:
         print("Error: Output texture timeline path not specified in config.")
         return None

    try:
        # Create mapper instance - NOTE: Audio analysis part is removed from this class now
        mapper = AudioTextureMapper(
            audio_timeline_path=audio_timeline_path,
            high_confidence_textures_path=high_conf_path,
            emotion_mapping_path=emotion_map_path
            # Removed device=device argument as it's no longer needed by the refactored mapper
        )
        
        # Generate texture timeline JSON
        print(f"Generating texture timeline based on {os.path.basename(audio_timeline_path)}...")
        texture_timeline = mapper.generate_texture_timeline(output_timeline_path)
        
        # Visualize timeline (optional, could be moved to evaluation)
        viz_path = os.path.join(output_dir, "texture_timeline_visualization.png")
        mapper.visualize_timeline(texture_timeline, viz_path)
        
        print(f"Texture mapping complete. Timeline saved to {output_timeline_path}")
        return output_timeline_path
    except Exception as e:
        print(f"Error during texture mapping: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def run_texture_blending(config, texture_timeline_path):
    """Blend textures and create displacement maps."""
    print("\n" + "="*80)
    print("Stage 2: Texture Blending & Displacement Map Generation")
    print("="*80)
    
    blend_config = config.get('texture_blending', {})
    output_dir = config.get('blending_output_dir')
    animation_data_path = blend_config.get('animation_data_path')
    results_path = blend_config.get('blending_results_path')
    
    # Input validation
    if not texture_timeline_path or not os.path.exists(texture_timeline_path):
        print(f"Error: Texture timeline path not found: {texture_timeline_path}")
        return None
    if not output_dir:
         print("Error: Blending output directory not specified in config.")
         return None
    if not animation_data_path:
         print("Error: Animation data output path not specified in config.")
         return None

    try:
        # Create blender instance
        blender = TextureBlender(texture_timeline_path, output_dir)
        
        # Process timeline using settings from config
        print("Blending textures and generating displacement maps...")
        results = blender.process_timeline(
            target_size=(blend_config.get('target_size', 512), blend_config.get('target_size', 512)),
            blur_kernel=blend_config.get('blur_kernel', 5),
            displacement_scale=blend_config.get('displacement_scale', 1.0)
        )
        
        # Save detailed results if path specified
        if results_path:
             try:
                 with open(results_path, 'w') as f: json.dump(results, f, indent=2)
                 print(f"Saved detailed blending results to {results_path}")
             except Exception as e: print(f"Error saving blending results: {e}")

        # Create summary visualization (optional, could be moved to evaluation)
        summary_path = os.path.join(output_dir, "blending_summary_visualization.png")
        blender.create_summary_visualization(results, summary_path)
        
        # Create animation data (crucial for next step)
        blender.create_animation_data(results, animation_data_path)
        
        print(f"Texture blending complete. Animation data saved to {animation_data_path}")
        return animation_data_path
    except Exception as e:
        print(f"Error during texture blending: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def run_parametric_design(config, animation_data_path):
    """Generate parametric design parameters for lamp."""
    print("\n" + "="*80)
    print("Stage 3: Parametric Lamp Design Generation")
    print("="*80)
    
    design_config = config.get('parametric_design', {})
    output_dir = config.get('parametric_output_dir')
    results_path = design_config.get('design_results_path')
    visualize = design_config.get('visualize_previews', True)

    # Input validation
    if not animation_data_path or not os.path.exists(animation_data_path):
        print(f"Error: Animation data path not found: {animation_data_path}")
        return None
    if not output_dir:
         print("Error: Parametric design output directory not specified in config.")
         return None

    try:
        # Create generator instance
        generator = ParametricDesignGenerator(animation_data_path, output_dir)
        
        # Update generator parameters from config if needed (optional refinement)
        # generator.base_radius = design_config.get('base_radius', 100.0) 
        # ... etc. (Or modify the generator class to accept config)
        
        # Process all time points, passing the relevant design config section
        print("Generating parametric design parameters...")
        results = generator.process_time_points(design_config=design_config, visualize=visualize)
        
        # Save results summary if path specified
        if results_path:
             try:
                 with open(results_path, 'w') as f: json.dump(results, f, indent=2)
                 print(f"Saved design results summary to {results_path}")
             except Exception as e: print(f"Error saving design results: {e}")

        # Generate Rhino script for the first result (as an example)
        if results:
            first_param_path = results[0]["parameters_path"]
            script_path = first_param_path.replace(".json", "_rhino.py")
            generator.generate_rhino_python_script(first_param_path, script_path)
        
        print(f"Parametric design generation complete. Results saved to {output_dir}")
        return results
    except Exception as e:
        print(f"Error during parametric design generation: {e}")
        import traceback
        print(traceback.format_exc())
        return None

# --- Main Execution ---

def main():
    """Run the complete pipeline from audio to parametric lamp design."""
    parser = argparse.ArgumentParser(description="Emotion-Driven Parametric Lamp Design Pipeline")
    parser.add_argument("--config", default="config/pipeline_config.yaml", help="Path to configuration file.")
    parser.add_argument("--audio", help="Path to audio file to analyze.")
    parser.add_argument("--device", choices=["cuda", "cpu"], help="Device to use for processing.")
    parser.add_argument("--skip_texture_mapping", action="store_true", help="Skip texture mapping stage.")
    parser.add_argument("--skip_blending", action="store_true", help="Skip texture blending & displacement stage.")
    parser.add_argument("--skip_parametric", action="store_true", help="Skip parametric design stage.")
    parser.add_argument("--dataset", choices=["dtd", "huggingface", "all"], default="all", 
                        help="Dataset to use: dtd, huggingface, or all (default)")
    parser.add_argument("--texture_timeline", help="Path to existing texture timeline JSON (if skipping mapping).")
    parser.add_argument("--animation_data", help="Path to existing animation data JSON (if skipping blending).")
    parser.add_argument("--output_dir", help="Base directory for all outputs.")
    # Add VAD support
    parser.add_argument("--vad_csv", help="Path to VAD CSV file for texture classification using the VAD model.")
    parser.add_argument("--classifier", choices=["emotion", "vad"], default="emotion",
                       help="Texture classifier to use: emotion (default) or vad (VAD-based).")
    
    args = parser.parse_args()
    
    # Load config
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, args.config) if not os.path.isabs(args.config) else args.config
    config = load_config(config_path)
    
    # Override config with command line args if provided
    if args.audio: config['audio_timeline_path'] = args.audio
    if args.device: config['device'] = args.device
    if args.output_dir: config['results_base_dir'] = args.output_dir
    if args.vad_csv: config['vad_csv_path'] = args.vad_csv
    
    # Set classifier type
    config['classifier_type'] = args.classifier
    
    # Add dataset preference to config
    config['dataset_preference'] = args.dataset
    
    # Set results directory based on dataset
    if not args.output_dir and args.dataset == 'huggingface':
        # Default to hugging_results for Hugging Face dataset
        config['hugging_results_dir'] = 'hugging_results'
    
    # Resolve relative paths in config
    config = resolve_paths(config, base_dir)
    
    # Ensure output directories exist
    ensure_directories(config)
    
    # Print configuration
    print("\nRunning Emotion-Driven Parametric Lamp Design Pipeline")
    print(f"Configuration: {config_path}")
    print(f"Audio timeline: {config.get('audio_timeline_path', 'Not specified')}")
    print(f"Dataset preference: {args.dataset}")
    print(f"Output directory: {config['results_base_dir']}")
    print(f"Device: {config.get('device', 'auto')}")
    print(f"Classifier: {config['classifier_type']}")
    if config.get('vad_csv_path'):
        print(f"VAD CSV: {config['vad_csv_path']}")
    
    # Run stages (with skip options)
    if args.skip_texture_mapping and args.texture_timeline:
        print(f"Skipping texture mapping, using provided timeline: {args.texture_timeline}")
        texture_timeline_path = args.texture_timeline
    else:
        texture_timeline_path = run_texture_mapping(config)
        if not texture_timeline_path:
            print("Texture mapping failed. Exiting.")
            sys.exit(1)
    
    if args.skip_blending and args.animation_data:
        print(f"Skipping texture blending, using provided animation data: {args.animation_data}")
        animation_data_path = args.animation_data
    else:
        animation_data_path = run_texture_blending(config, texture_timeline_path)
        if not animation_data_path:
            print("Texture blending failed. Exiting.")
            sys.exit(1)
    
    if not args.skip_parametric:
        design_output_path = run_parametric_design(config, animation_data_path)
        if not design_output_path:
            print("Parametric design generation failed. Exiting.")
            sys.exit(1)
    else:
        print("Skipping parametric design generation.")
    
    print("\nPipeline completed successfully!")
    print(f"Results saved in: {config['results_base_dir']}")

if __name__ == "__main__":
    main()
