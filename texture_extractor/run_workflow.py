#!/usr/bin/env python
"""
This script automates the complete texture processing workflow:
1. Classify textures by emotion using texture_emotion_classifier.py
2. Generate depth maps for high-confidence images using depth_converter.py
3. Visualize results using visualize_output_maps.py
"""

import os
import subprocess
import argparse
import sys
from pathlib import Path

def run_command(command, description):
    """Run a shell command and print its output."""
    print(f"\n===== {description} =====")
    print(f"Running: {' '.join(command)}")
    
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Print output in real-time
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
            
        process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0:
            print(f"Command failed with return code {return_code}")
            return False
        return True
    
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    # Change working directory to script location to ensure consistent paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    parser = argparse.ArgumentParser(description="Run the complete texture processing workflow.")
    parser.add_argument("--input_dir", default="dtd/images", help="Directory containing input texture images (default: dtd/images)")
    parser.add_argument("--confidence", type=float, default=0.6, help="Confidence threshold for emotion classification (default: 0.6)")
    parser.add_argument("--skip_classification", action="store_true", help="Skip the classification step if already done")
    parser.add_argument("--skip_depth", action="store_true", help="Skip the depth map generation step if already done")
    parser.add_argument("--skip_visualization", action="store_true", help="Skip the visualization step")
    parser.add_argument("--device", choices=["cuda", "cpu"], default=None, help="Device to use (default: auto-detect)")
    args = parser.parse_args()

    # Ensure input_dir is correctly formatted (relative to script directory)
    if not os.path.isabs(args.input_dir):
        input_dir = os.path.join(script_dir, args.input_dir)
    else:
        input_dir = args.input_dir
        
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' doesn't exist")
        return

    # Ensure results directory exists
    results_dir = os.path.join(script_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Ensure depth maps directory exists
    depth_dir = os.path.join(results_dir, "depth_maps")
    os.makedirs(depth_dir, exist_ok=True)
    
    # Setup base command with Python executable
    python_cmd = [sys.executable]
    
    # 1. Run texture emotion classification if not skipped
    if not args.skip_classification:
        classification_cmd = python_cmd + [
            os.path.join(script_dir, "texture_emotion_classifier.py"),
            "--input_dir", input_dir,
            "--confidence_threshold", str(args.confidence)
        ]
        
        if args.device:
            classification_cmd.extend(["--device", args.device])
        
        success = run_command(classification_cmd, "Classifying texture images by emotion")
        if not success:
            print("Classification step failed. Stopping workflow.")
            return
    else:
        print("\n===== Skipping classification step as requested =====")
    
    # Check if high confidence file exists
    high_conf_file = os.path.join(results_dir, "high_confidence_images.txt")
    if not os.path.exists(high_conf_file):
        print(f"Error: High confidence image list not found at {high_conf_file}")
        print("Please run the classification step first or check for errors.")
        return
    
    # 2. Generate depth maps if not skipped
    if not args.skip_depth:
        depth_cmd = python_cmd + [
            os.path.join(script_dir, "depth_converter.py"),
            "--image_list_file", high_conf_file,
            "--output_dir", depth_dir
        ]
        
        if args.device:
            depth_cmd.extend(["--device", args.device])
        
        success = run_command(depth_cmd, "Generating depth maps for high-confidence images")
        if not success:
            print("Depth map generation step failed. Continuing to visualization if requested.")
    else:
        print("\n===== Skipping depth map generation step as requested =====")
    
    # 3. Visualize results if not skipped
    if not args.skip_visualization:
        visualization_cmd = python_cmd + [
            os.path.join(script_dir, "visualize_output_maps.py"),
            "--depth_dir", depth_dir,
            "--original_dir", input_dir,
            "--high_confidence_file", high_conf_file,
            "--output_prefix", "emotion_depth"
        ]
        
        success = run_command(visualization_cmd, "Visualizing depth maps with original images")
        if not success:
            print("Visualization step failed.")
    else:
        print("\n===== Skipping visualization step as requested =====")
    
    print("\n===== Workflow Complete =====")
    print(f"Results directory: {os.path.abspath(results_dir)}")
    if not args.skip_visualization:
        print(f"Generated visualizations:")
        print(f"- HTML Gallery: {os.path.abspath(os.path.join(results_dir, 'emotion_depth_gallery.html'))}")
        print(f"- Grid Image: {os.path.abspath(os.path.join(results_dir, 'emotion_depth_grid.png'))}")

if __name__ == "__main__":
    main() 