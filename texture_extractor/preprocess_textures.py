#!/usr/bin/env python
"""
This script handles the texture preprocessing workflow:
1. Classify textures by emotion using src.texture_classifier
2. Generate depth maps for high-confidence images using src.depth_generator
   (Depth generation is optional if using Hugging Face dataset with normal maps)
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
import time

# Ensure the src directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Import the refactored modules from src
try:
    # Assuming texture_classifier.py has a main function or class to run classification
    import texture_classifier 
    # Import new VAD-based classifier if available
    try:
        import vad_texture_classifier
        vad_classifier_available = True
    except ImportError:
        vad_classifier_available = False
        print("VAD texture classifier not available - will use traditional emotion classifier.")
    
    # Assuming depth_generator.py has a main function or class to run depth generation
    import depth_generator
    # Import utils for dataset detection
    from utils import detect_dataset_type, find_textures_by_dataset, is_normal_map_available
except ImportError as e:
    print(f"Error importing modules from src: {e}")
    print(f"Please ensure __init__.py exists in {src_dir} and all module files are present.")
    sys.exit(1)

# --- Config Loading & Path Resolution (Similar to main.py) ---

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
    
    # Determine the results base directory
    if 'hugging_data_dir' in resolved_config:
        results_base = os.path.join(base_dir, resolved_config.get('hugging_results_dir', 'hugging_results'))
    else:
        results_base = os.path.join(base_dir, resolved_config.get('results_base_dir', 'results'))
    
    # Resolve input paths
    if 'original_textures_dir' in resolved_config and not os.path.isabs(resolved_config['original_textures_dir']):
        resolved_config['original_textures_dir'] = os.path.join(base_dir, resolved_config['original_textures_dir'])
    
    if 'hugging_data_dir' in resolved_config and not os.path.isabs(resolved_config['hugging_data_dir']):
        resolved_config['hugging_data_dir'] = os.path.join(base_dir, resolved_config['hugging_data_dir'])
    
    # Add VAD CSV path resolution
    if 'vad_csv_path' in resolved_config and not os.path.isabs(resolved_config['vad_csv_path']):
        resolved_config['vad_csv_path'] = os.path.join(base_dir, resolved_config['vad_csv_path'])
        
    # Resolve output paths relative to results base
    resolved_config['results_base_dir'] = results_base
    
    # Classification outputs
    cls_output_dir = os.path.join(results_base, 'classification')
    resolved_config['classification_output_dir'] = cls_output_dir
    
    # Depth map outputs
    depth_output_dir = os.path.join(results_base, 'depth_maps')
    resolved_config['depth_maps_output_dir'] = depth_output_dir
    
    # Classification specific paths
    cls_conf = resolved_config.get('classification', {})
    cls_conf['high_confidence_list_path'] = os.path.join(cls_output_dir, cls_conf.get('high_confidence_list_filename', 'high_confidence_textures.txt'))
    cls_conf['classification_results_path'] = os.path.join(resolved_config['classification_output_dir'], cls_conf.get('classification_results_filename', 'classification_results.txt'))
    resolved_config['classification'] = cls_conf

    # Depth generation doesn't have specific filenames in config, only output dir
    
    return resolved_config

def create_directories(config):
    """Ensure that all required output directories exist."""
    dirs_to_create = [
        config['results_base_dir'],
        config['classification_output_dir'],
        config['depth_maps_output_dir'],
    ]
    
    for d in dirs_to_create:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory {d}: {e}")
            return False
    return True

# --- Preprocessing Stages ---

def run_classification(config, dataset_type=None):
    """
    Run texture classification using the imported module.
    
    Args:
        config: Configuration dictionary
        dataset_type: 'dtd', 'huggingface', or None (for both)
    """
    print("\n" + "="*80)
    print(f"Stage 1: Texture Classification (Dataset: {dataset_type or 'all'})")
    print("="*80)
    
    cls_config = config.get('classification', {})
    
    # Determine input directory based on dataset type
    if dataset_type == 'huggingface':
        input_dir = os.path.join(config.get('hugging_data_dir', 'data/hugging_data'), 'color')
    elif dataset_type == 'dtd':
        input_dir = config.get('original_textures_dir')
    else:
        # When no specific dataset is chosen, use both
        # We'll handle the merged case differently
        dtd_dir = config.get('original_textures_dir')
        hf_dir = os.path.join(config.get('hugging_data_dir', 'data/hugging_data'), 'color')
        
        # Find all textures from both datasets
        texture_paths = find_textures_by_dataset(os.path.dirname(script_dir))
        
        if not texture_paths:
            print(f"Error: No texture files found in either dataset.")
            return False

        # Create a temporary directory list file
        temp_list_file = os.path.join(config['classification_output_dir'], 'all_texture_paths.txt')
        try:
            os.makedirs(os.path.dirname(temp_list_file), exist_ok=True)
            with open(temp_list_file, 'w') as f:
                for path in texture_paths:
                    f.write(f"{path}\n")
            input_dir = temp_list_file
            print(f"Created temporary file list with {len(texture_paths)} textures.")
        except Exception as e:
            print(f"Error creating texture list file: {e}")
            return False
    
    output_list_path = cls_config.get('high_confidence_list_path')
    output_results_path = cls_config.get('classification_results_path')
    confidence = cls_config.get('confidence_threshold', 0.6)
    device_pref = config.get('device') # cuda, cpu, or None
    
    # Check for VAD classifier usage
    classifier_type = config.get('classifier_type', 'emotion')
    vad_csv_path = config.get('vad_csv_path', None)
    
    # Show warning if VAD classifier is requested but not available
    if classifier_type == 'vad' and not vad_classifier_available:
        print("Warning: VAD classifier requested but not available. Using emotion classifier instead.")
        classifier_type = 'emotion'
    
    # Show warning if VAD classifier is requested but no CSV file is provided
    if classifier_type == 'vad' and not vad_csv_path:
        print("Warning: VAD classifier requested but no VAD CSV file provided. Using emotion classifier instead.")
        classifier_type = 'emotion'
    
    # Input validation for single dataset case
    if dataset_type in ['dtd', 'huggingface'] and (not input_dir or not os.path.exists(input_dir)):
        print(f"Error: Texture directory for {dataset_type} not found: {input_dir}")
        return False
    
    if not output_list_path or not output_results_path:
         print("Error: Classification output paths not specified in config.")
         return False

    try:
        print(f"Running {classifier_type} classification on: {input_dir}")
        print(f"Confidence threshold: {confidence}")
        print(f"Saving high-confidence list to: {output_list_path}")
        print(f"Saving detailed results to: {output_results_path}")
        
        # Choose classifier based on type
        if classifier_type == 'vad' and vad_classifier_available and vad_csv_path:
            print(f"Using VAD-based texture classifier with VAD data from: {vad_csv_path}")
            # Call the VAD classifier with VAD CSV path
            success = vad_texture_classifier.run_classification_pipeline(
                input_dir=input_dir,
                confidence_threshold=confidence,
                device_pref=device_pref,
                output_list_path=output_list_path,
                output_results_path=output_results_path,
                is_file_list=(dataset_type is None),  # If we're using both datasets, we pass a file list
                vad_csv_path=vad_csv_path
            )
        else:
            # Call the original emotion classifier
            print("Using traditional emotion-based texture classifier")
            success = texture_classifier.run_classification_pipeline(
                input_dir=input_dir,
                confidence_threshold=confidence,
                device_pref=device_pref,
                output_list_path=output_list_path,
                output_results_path=output_results_path,
                is_file_list=(dataset_type is None)  # If we're using both datasets, we pass a file list
            )
            
        if not success:
             print("Classification pipeline function returned failure.")
             return False

        print("Classification finished.")
        return True
        
    except Exception as e:
        print(f"Error during classification stage: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def run_depth_generation(config, dataset_type=None):
    """
    Run depth map generation for high-confidence textures.
    
    Args:
        config: Configuration dictionary
        dataset_type: 'dtd', 'huggingface', or None (for both)
    """
    print("\n" + "="*80)
    print(f"Stage 2: Depth Map Generation (Dataset: {dataset_type or 'all'})")
    print("="*80)

    # Skip depth generation for huggingface dataset if normal maps are available
    if dataset_type == 'huggingface':
        normal_map_dir = os.path.join(config.get('hugging_data_dir', 'data/hugging_data'), 'normal')
        if is_normal_map_available(normal_map_dir):
            print(f"Normal maps already available at: {normal_map_dir}")
            print("Skipping depth map generation for Hugging Face dataset.")
            return True
    
    cls_config = config.get('classification', {})
    high_conf_path = cls_config.get('high_confidence_list_path')
    output_dir = config.get('depth_maps_output_dir')
    device_pref = config.get('device')

    # Input validation
    if not high_conf_path or not os.path.exists(high_conf_path):
        print(f"Error: High confidence texture list not found: {high_conf_path}")
        print("Please run texture classification first.")
        return False
    if not output_dir:
         print("Error: Depth maps output directory not specified in config.")
         return False

    try:
        # Call the module's main function
        print(f"Generating depth maps for high-confidence textures...")
        print(f"Input list: {high_conf_path}")
        print(f"Output directory: {output_dir}")
        
        # Use the refactored depth generator interface
        success = depth_generator.run_depth_generation_pipeline(
            high_confidence_list_path=high_conf_path,
            output_dir=output_dir,
            device_pref=device_pref
        )
        
        if not success:
            print("Depth generation pipeline function returned failure.")
            return False
        
        print("Depth map generation complete.")
        return True
        
    except Exception as e:
        print(f"Error during depth map generation: {e}")
        import traceback
        print(traceback.format_exc())
        return False

# --- Main Execution ---

def main():
    """Run the texture preprocessing pipeline."""
    parser = argparse.ArgumentParser(description="Preprocess textures for the pipeline")
    parser.add_argument("--config", default="config/pipeline_config.yaml", help="Path to configuration file.")
    parser.add_argument("--dataset", choices=["dtd", "huggingface", "all"], default="all", help="Dataset to process.")
    parser.add_argument("--skip_classification", action="store_true", help="Skip texture classification stage.")
    parser.add_argument("--skip_depth", action="store_true", help="Skip depth map generation stage.")
    parser.add_argument("--device", choices=["cuda", "cpu"], help="Device to use for processing.")
    # Add VAD support
    parser.add_argument("--vad_csv", help="Path to VAD CSV file for texture classification using the VAD model.")
    parser.add_argument("--classifier", choices=["emotion", "vad"], default="emotion",
                       help="Texture classifier to use: emotion (default) or vad (VAD-based).")
    
    args = parser.parse_args()
    
    # Load config
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, args.config) if not os.path.isabs(args.config) else args.config
    config = load_config(config_path)
    
    # Override config with command line args
    if args.device:
        config['device'] = args.device
    if args.vad_csv:
        config['vad_csv_path'] = args.vad_csv
    
    # Set classifier type
    config['classifier_type'] = args.classifier
    
    # Resolve paths in config
    config = resolve_paths(config, base_dir)
    
    # Create output directories
    if not create_directories(config):
        print("Failed to create output directories. Exiting.")
        sys.exit(1)
    
    # Begin processing
    print("\nTexture Preprocessing Workflow")
    print(f"Configuration: {config_path}")
    print(f"Dataset: {args.dataset}")
    print(f"Device: {config.get('device', 'auto')}")
    print(f"Classifier: {config['classifier_type']}")
    if config.get('vad_csv_path'):
        print(f"VAD CSV: {config['vad_csv_path']}")
    
    # Run the selected stages
    if not args.skip_classification:
        if not run_classification(config, args.dataset):
            print("Texture classification failed. Exiting.")
            sys.exit(1)
    else:
        print("Skipping texture classification stage.")
    
    if not args.skip_depth:
        if not run_depth_generation(config, args.dataset):
            print("Depth map generation failed. Exiting.")
            sys.exit(1)
    else:
        print("Skipping depth map generation stage.")
    
    print("\nPreprocessing completed successfully!")
    print(f"Results saved in: {config['results_base_dir']}")

if __name__ == "__main__":
    # Measure execution time
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"Total execution time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
