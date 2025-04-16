#!/usr/bin/env python
"""
Visualize classification results from the texture classification process.
This script creates a visualization showing sample images, their top emotions,
and the distribution of emotions across all classified images.
"""

import os
import sys
import argparse
import re
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
import random

# Function to read classification results
def read_classification_results(results_file):
    """Read the classification results file and extract image paths and emotion scores."""
    results = []
    current_image = None
    emotions = {}
    
    with open(results_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Extract image path
        if line.startswith('Image:'):
            if current_image and emotions:
                results.append({
                    'image_path': current_image,
                    'emotions': emotions,
                    'passed_threshold': passed_threshold
                })
            
            current_image = line[6:].strip()
            emotions = {}
            passed_threshold = False
        
        # Extract emotion scores
        elif line.startswith('-'):
            parts = line[1:].strip().split(':')
            if len(parts) == 2:
                emotion = parts[0].strip()
                score = float(parts[1].strip())
                emotions[emotion] = score
        
        # Extract threshold information
        elif line.startswith('Passed Threshold'):
            passed_threshold = 'YES' in line
            
            # End of an entry, add to results
            if current_image and emotions:
                results.append({
                    'image_path': current_image,
                    'emotions': emotions,
                    'passed_threshold': passed_threshold
                })
                current_image = None
                emotions = {}
        
        i += 1
    
    return results

# Function to visualize sample images with their top emotions
def visualize_samples(results, output_file, num_samples=10, only_high_confidence=True):
    """Create a grid of sample images with their top emotions."""
    filtered_results = [r for r in results if r['passed_threshold']] if only_high_confidence else results
    
    if not filtered_results:
        print("No results to visualize!")
        return
    
    # Select random samples
    samples = random.sample(filtered_results, min(num_samples, len(filtered_results)))
    
    # Calculate grid dimensions
    cols = min(5, num_samples)
    rows = (num_samples + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(15, 3 * rows))
    if rows == 1 and cols == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    for i, (ax, sample) in enumerate(zip(axes, samples)):
        # Load and display the image
        try:
            img = Image.open(sample['image_path'])
            ax.imshow(img)
            
            # Get top emotion and score
            top_emotion = max(sample['emotions'].items(), key=lambda x: x[1])
            
            # Set title with emotion and score
            ax.set_title(f"{top_emotion[0]}: {top_emotion[1]:.2f}")
            ax.axis('off')
        except Exception as e:
            print(f"Error displaying image {sample['image_path']}: {e}")
            ax.text(0.5, 0.5, "Image Load Error", ha='center', va='center')
            ax.axis('off')
    
    # Hide any unused axes
    for i in range(len(samples), len(axes)):
        axes[i].axis('off')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    print(f"Sample visualization saved to {output_file}")
    plt.close()

# Function to visualize emotion distribution
def visualize_emotion_distribution(results, output_file, only_high_confidence=True):
    """Create a bar chart showing the distribution of top emotions."""
    filtered_results = [r for r in results if r['passed_threshold']] if only_high_confidence else results
    
    if not filtered_results:
        print("No results to visualize!")
        return
    
    # Count the top emotions
    emotion_counts = {}
    for result in filtered_results:
        top_emotion = max(result['emotions'].items(), key=lambda x: x[1])[0]
        emotion_counts[top_emotion] = emotion_counts.get(top_emotion, 0) + 1
    
    # Sort emotions by count
    emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
    emotion_names = [e[0] for e in emotions]
    counts = [e[1] for e in emotions]
    
    # Create the bar chart
    plt.figure(figsize=(12, 6))
    bars = plt.bar(emotion_names, counts, color='skyblue')
    
    # Add labels and values on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{height}', ha='center', va='bottom')
    
    plt.title('Distribution of Top Emotions in Classified Textures')
    plt.xlabel('Emotion')
    plt.ylabel('Count')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    plt.savefig(output_file, dpi=150)
    print(f"Emotion distribution visualization saved to {output_file}")
    plt.close()

def main():
    """Main function to run the visualization."""
    parser = argparse.ArgumentParser(description="Visualize texture classification results")
    parser.add_argument("--results", default="hugging_results/classification/classification_results.txt",
                        help="Path to classification results file")
    parser.add_argument("--output_dir", default="hugging_results/classification/visualizations",
                        help="Directory to save visualizations")
    parser.add_argument("--samples", type=int, default=10, 
                        help="Number of sample images to display")
    parser.add_argument("--only_high_confidence", action="store_true", 
                        help="Only include images that passed the confidence threshold")
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Read classification results
    print(f"Reading classification results from {args.results}")
    results = read_classification_results(args.results)
    print(f"Found {len(results)} classified images")
    
    # Filter for high confidence results if needed
    high_confidence = [r for r in results if r['passed_threshold']]
    print(f"Of which {len(high_confidence)} passed the confidence threshold")
    
    # Use high confidence flag to determine which results to visualize
    use_only_high_confidence = args.only_high_confidence
    
    # If there are no high confidence results but user requested only high confidence,
    # warn and fall back to all results
    if use_only_high_confidence and len(high_confidence) == 0:
        print("Warning: No high confidence results found. Showing all results instead.")
        use_only_high_confidence = False
    
    # Visualize sample images
    samples_file = os.path.join(args.output_dir, "sample_classifications.png")
    visualize_samples(results, samples_file, args.samples, use_only_high_confidence)
    
    # Visualize emotion distribution
    distribution_file = os.path.join(args.output_dir, "emotion_distribution.png")
    visualize_emotion_distribution(results, distribution_file, use_only_high_confidence)
    
    print("Visualization complete. Files saved to:")
    print(f"  - {samples_file}")
    print(f"  - {distribution_file}")

if __name__ == "__main__":
    main() 