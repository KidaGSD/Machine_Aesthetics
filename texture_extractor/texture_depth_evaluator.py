#!/usr/bin/env python
"""
Texture-Depth Evaluator Script

This script matches high-confidence texture images with their depth maps
and creates visualizations that display them in a meaningful space,
organized by emotion classification.
"""

import os
import re
import random
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
import argparse
from tqdm import tqdm
import pandas as pd
import matplotlib.gridspec as gridspec
from matplotlib.colors import ListedColormap
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import shutil

def load_high_confidence_images(file_path):
    """Load list of high confidence image paths from a file."""
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error loading high confidence image list: {e}")
        return []

def extract_image_info(image_path):
    """Extract category and filename from image path."""
    # Expected path format: .../dtd/images/category/filename.jpg
    try:
        parts = image_path.split(os.sep)
        # Find the 'images' index, then category is next, and filename after that
        for i, part in enumerate(parts):
            if part == 'images':
                category = parts[i+1]
                filename = parts[i+2]
                return category, os.path.splitext(filename)[0]
    except Exception:
        pass
    
    # Fallback: try to get category and name from regex
    try:
        match = re.search(r'([a-zA-Z-]+)_(\d+)', os.path.basename(image_path))
        if match:
            return match.group(1), match.group(0).split('.')[0]
    except:
        pass
        
    print(f"Warning: Could not extract category and filename from {image_path}")
    return None, None

def find_matching_depth_map(orig_category, orig_filename, depth_dir):
    """Find corresponding depth map for an original image."""
    # Try exact match first
    potential_depth_path = os.path.join(depth_dir, 'images', orig_category, f"{orig_filename}.png")
    if os.path.exists(potential_depth_path):
        return potential_depth_path
    
    # Try matching just the filename without extension
    filename_base = orig_filename.split('.')[0]
    potential_depth_path = os.path.join(depth_dir, 'images', orig_category, f"{filename_base}.png")
    if os.path.exists(potential_depth_path):
        return potential_depth_path
    
    return None

def extract_emotion_from_classifications(image_path, classification_file):
    """Extract the top emotion label for an image from the classification results file."""
    try:
        with open(classification_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        image_basename = os.path.basename(image_path)
        start_line = -1
        
        # Find the line containing our image path
        for i, line in enumerate(lines):
            if image_basename in line and line.startswith("Image:"):
                start_line = i
                break
        
        if start_line >= 0 and start_line < len(lines) - 1:
            # Look for emotions in the next few lines
            for j in range(start_line + 1, min(start_line + 10, len(lines))):
                line = lines[j].strip()
                if line.startswith("- ") and ":" in line:
                    # Extract emotion and confidence
                    parts = line[2:].split(":", 1)
                    if len(parts) == 2:
                        emotion = parts[0].strip()
                        confidence = float(parts[1].strip())
                        return emotion, confidence
        
        return None, None
    except Exception as e:
        print(f"Error extracting emotion from classifications: {e}")
        return None, None

def classify_images_directly(image_paths):
    """Generate emotion labels directly for a list of image paths using a simple embedded classifier."""
    try:
        import torch
        import clip
        from PIL import Image
        
        # Define emotions
        EMOTIONS = ['excited', 'peaceful', 'sad', 'fearful', 'angry', 'disgusted', 'surprised']
        
        # Load CLIP model
        print("Loading CLIP model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        
        # Create text templates for emotions
        templates = [f"This texture appears {emotion}." for emotion in EMOTIONS]
        text_inputs = clip.tokenize(templates).to(device)
        
        # Encode text
        with torch.no_grad():
            text_features = model.encode_text(text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        # Process each image
        labels = {}
        for img_path in tqdm(image_paths, desc="Classifying Images"):
            try:
                # Load and preprocess image
                image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
                
                # Encode image
                with torch.no_grad():
                    image_features = model.encode_image(image)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                # Calculate similarity
                similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
                
                # Convert to list of tuples (emotion, score)
                similarity = similarity.squeeze().cpu().numpy()
                sorted_emotions = sorted(
                    [(emotion, float(score)) for emotion, score in zip(EMOTIONS, similarity)],
                    key=lambda x: x[1],
                    reverse=True
                )
                
                # Store result
                labels[img_path] = sorted_emotions[0]  # Store only top emotion
                
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
        
        return labels
    except ImportError:
        print("CLIP not available. Using random classification as fallback.")
        EMOTIONS = ['excited', 'peaceful', 'sad', 'fearful', 'angry', 'disgusted', 'surprised']
        return {path: (random.choice(EMOTIONS), random.random()) for path in image_paths}

def create_image_features(images):
    """Extract simple features from images for visualization."""
    features = []
    for img_path in tqdm(images, desc="Extracting image features"):
        try:
            img = Image.open(img_path).convert('RGB')
            img = img.resize((64, 64))  # Resize for consistency
            # Simple feature: average RGB values in grid cells
            img_array = np.array(img)
            # Split into 4x4 grid
            grid_features = []
            h, w = img_array.shape[0], img_array.shape[1]
            grid_h, grid_w = h // 4, w // 4
            for i in range(4):
                for j in range(4):
                    cell = img_array[i*grid_h:(i+1)*grid_h, j*grid_w:(j+1)*grid_w]
                    avg_color = np.mean(cell, axis=(0, 1))
                    grid_features.extend(avg_color)
            features.append(grid_features)
        except Exception as e:
            print(f"Error extracting features from {img_path}: {e}")
            # Use zeros as fallback
            features.append(np.zeros(4*4*3))
    
    return np.array(features)

def create_depth_map_features(depth_maps):
    """Extract features from depth maps for visualization."""
    features = []
    for depth_path in tqdm(depth_maps, desc="Extracting depth map features"):
        try:
            if depth_path is None:
                # Use zeros for missing depth maps
                features.append(np.zeros(4*4))
                continue
                
            img = Image.open(depth_path).convert('L')  # Convert to grayscale
            img = img.resize((64, 64))  # Resize for consistency
            # Simple feature: average depth values in grid cells
            img_array = np.array(img)
            # Split into 4x4 grid
            grid_features = []
            h, w = img_array.shape[0], img_array.shape[1]
            grid_h, grid_w = h // 4, w // 4
            for i in range(4):
                for j in range(4):
                    cell = img_array[i*grid_h:(i+1)*grid_h, j*grid_w:(j+1)*grid_w]
                    avg_depth = np.mean(cell)
                    grid_features.append(avg_depth)
            features.append(grid_features)
        except Exception as e:
            print(f"Error extracting features from {depth_path}: {e}")
            # Use zeros as fallback
            features.append(np.zeros(4*4))
    
    return np.array(features)

def create_combined_features(image_features, depth_features):
    """Combine image and depth features."""
    if len(image_features) != len(depth_features):
        print(f"Warning: Different number of image features ({len(image_features)}) and depth features ({len(depth_features)})")
        min_len = min(len(image_features), len(depth_features))
        image_features = image_features[:min_len]
        depth_features = depth_features[:min_len]
    
    # Normalize each feature set
    if len(image_features) > 0:
        image_features = (image_features - np.mean(image_features, axis=0)) / (np.std(image_features, axis=0) + 1e-10)
    
    if len(depth_features) > 0:
        depth_features = (depth_features - np.mean(depth_features, axis=0)) / (np.std(depth_features, axis=0) + 1e-10)
    
    # Combine
    return np.hstack([image_features, depth_features])

def create_tsne_visualization(features, emotions, output_path="emotion_depth_tsne.png"):
    """Create t-SNE visualization of image features colored by emotion."""
    if len(features) == 0:
        print("No features to visualize")
        return
    
    # Map emotions to numbers
    unique_emotions = sorted(set(emotions))
    emotion_to_id = {emotion: i for i, emotion in enumerate(unique_emotions)}
    emotion_ids = [emotion_to_id[emotion] for emotion in emotions]
    
    # Apply dimensionality reduction
    print("Applying t-SNE...")
    # First reduce with PCA if we have high dimensional features
    if features.shape[1] > 50:
        pca = PCA(n_components=50)
        features = pca.fit_transform(features)
    
    tsne = TSNE(n_components=2, random_state=42)
    reduced_features = tsne.fit_transform(features)
    
    # Create colormap for emotions
    cmap = plt.cm.get_cmap('tab10', len(unique_emotions))
    
    # Create plot
    plt.figure(figsize=(12, 10))
    scatter = plt.scatter(reduced_features[:, 0], reduced_features[:, 1], 
                          c=emotion_ids, cmap=cmap, alpha=0.7)
    
    # Add legend
    legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                   markerfacecolor=cmap(emotion_to_id[emotion]), 
                                   markersize=10, label=emotion)
                       for emotion in unique_emotions]
    plt.legend(handles=legend_elements, title="Emotions")
    
    plt.title('t-SNE Visualization of Texture-Depth Space by Emotion')
    plt.xlabel('t-SNE dimension 1')
    plt.ylabel('t-SNE dimension 2')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"Saved t-SNE visualization to {output_path}")
    plt.close()

def copy_images_to_web_dir(image_paths, web_dir):
    """Copy images to a web directory for better browser access."""
    os.makedirs(web_dir, exist_ok=True)
    web_paths = []
    
    for img_path in tqdm(image_paths, desc="Copying images to web directory"):
        if img_path and os.path.exists(img_path):
            # Create a destination filename
            dest_filename = os.path.basename(img_path)
            dest_path = os.path.join(web_dir, dest_filename)
            
            # Copy the file
            try:
                shutil.copy2(img_path, dest_path)
                web_paths.append(dest_path)
            except Exception as e:
                print(f"Error copying {img_path}: {e}")
                web_paths.append(None)
        else:
            web_paths.append(None)
    
    return web_paths

def create_gallery_visualization(original_images, depth_maps, emotions, confidences,
                               output_path="emotion_depth_gallery.html", max_samples=100):
    """Create an HTML gallery of original images and their depth maps, grouped by emotion."""
    if len(original_images) == 0:
        print("No images to visualize")
        return
    
    # Create web directory for images
    web_dir = os.path.join(os.path.dirname(output_path), "web_gallery")
    os.makedirs(web_dir, exist_ok=True)
    
    # Web subdirectories
    orig_web_dir = os.path.join(web_dir, "originals")
    depth_web_dir = os.path.join(web_dir, "depths")
    
    print("Copying images to web directory for better browser compatibility...")
    web_orig_paths = copy_images_to_web_dir([p for p in original_images if p and os.path.exists(p)], orig_web_dir)
    web_depth_paths = copy_images_to_web_dir([p for p in depth_maps if p and os.path.exists(p)], depth_web_dir)
    
    # Create lookup dictionaries for quick access
    orig_web_lookup = {os.path.basename(orig): web_path for orig, web_path in zip(original_images, web_orig_paths) if orig and web_path}
    depth_web_lookup = {os.path.basename(depth): web_path for depth, web_path in zip(depth_maps, web_depth_paths) if depth and web_path}
    
    # Function to get web path
    def get_web_path(img_path, is_depth=False):
        if img_path and os.path.exists(img_path):
            basename = os.path.basename(img_path)
            lookup = depth_web_lookup if is_depth else orig_web_lookup
            if basename in lookup:
                return os.path.relpath(lookup[basename], os.path.dirname(output_path))
        return None
    
    # Group by emotion
    emotion_groups = {}
    for i, emotion in enumerate(emotions):
        if emotion not in emotion_groups:
            emotion_groups[emotion] = []
        
        original_path = original_images[i]
        depth_path = depth_maps[i] if i < len(depth_maps) else None
        confidence = confidences[i] if i < len(confidences) else None
        
        emotion_groups[emotion].append((original_path, depth_path, confidence))
    
    # Create HTML content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Texture-Depth Emotion Gallery</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }
            h1 { text-align: center; color: #343a40; margin-bottom: 30px; }
            h2 { color: #495057; margin-top: 30px; border-bottom: 2px solid #ced4da; padding-bottom: 10px; }
            .emotion-section { margin-bottom: 40px; }
            .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); grid-gap: 20px; }
            .item { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.3s; }
            .item:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.15); }
            .image-container { display: flex; justify-content: space-between; height: 200px; }
            .image-container img { width: 49.5%; height: 100%; object-fit: cover; }
            .image-container .depth-image { filter: hue-rotate(180deg); }
            .caption { padding: 15px; font-size: 14px; color: #495057; }
            .filename { font-weight: bold; margin-bottom: 5px; }
            .confidence { color: #6c757d; font-style: italic; margin-top: 5px; }
            .missing { background: #f8d7da; color: #721c24; text-align: center; padding: 15px; display: flex; align-items: center; justify-content: center; }
            .controls { margin-bottom: 20px; text-align: center; }
            button { padding: 8px 16px; margin: 0 5px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background-color: #0069d9; }
            .container { max-width: 1200px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Texture-Depth Emotion Gallery</h1>
            <div class="controls">
                <button onclick="showAll()">Show All</button>
    """
    
    # Add buttons for each emotion
    for emotion in sorted(emotion_groups.keys()):
        html_content += f'<button onclick="showOnly(\'{emotion}\')">{emotion}</button>'
    
    html_content += """
            </div>
    """
    
    # Add sections for each emotion
    for emotion in sorted(emotion_groups.keys()):
        samples = emotion_groups[emotion]
        if max_samples and len(samples) > max_samples:
            print(f"Limiting {emotion} to {max_samples} samples (from {len(samples)})")
            samples = random.sample(samples, max_samples)
        
        html_content += f"""
        <div class="emotion-section" id="section-{emotion}">
            <h2>{emotion.capitalize()} Textures ({len(samples)} samples)</h2>
            <div class="gallery">
        """
        
        for orig_path, depth_path, confidence in samples:
            orig_filename = os.path.basename(orig_path)
            confidence_html = f'<div class="confidence">Confidence: {confidence:.4f}</div>' if confidence else ''
            
            # Get web paths
            web_orig_path = get_web_path(orig_path)
            img_src = web_orig_path if web_orig_path else "missing.png"
            
            # Handle missing depth map
            if depth_path and os.path.exists(depth_path):
                web_depth_path = get_web_path(depth_path, is_depth=True)
                depth_html = f'<img src="{web_depth_path}" alt="Depth map" class="depth-image">' if web_depth_path else '<div class="missing">Depth map not available</div>'
            else:
                depth_html = '<div class="missing">Depth map not available</div>'
            
            html_content += f"""
            <div class="item">
                <div class="image-container">
                    <img src="{img_src}" alt="Original texture">
                    {depth_html}
                </div>
                <div class="caption">
                    <div class="filename">{orig_filename}</div>
                    Category: {extract_image_info(orig_path)[0]}
                    {confidence_html}
                </div>
            </div>
            """
        
        html_content += """
            </div>
        </div>
        """
    
    # Add JavaScript for filtering
    html_content += """
        <script>
            function showAll() {
                const sections = document.querySelectorAll('.emotion-section');
                sections.forEach(section => {
                    section.style.display = 'block';
                });
            }
            
            function showOnly(emotion) {
                const sections = document.querySelectorAll('.emotion-section');
                sections.forEach(section => {
                    if (section.id === `section-${emotion}`) {
                        section.style.display = 'block';
                    } else {
                        section.style.display = 'none';
                    }
                });
            }
        </script>
        </div>
    </body>
    </html>
    """
    
    # Write to file
    try:
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(html_content)
        print(f"Created gallery visualization at {output_path}")
        print(f"NOTE: To view the gallery in a browser, open {os.path.abspath(output_path)}")
        print(f"Web gallery images located at: {os.path.abspath(web_dir)}")
    except Exception as e:
        print(f"Error creating gallery: {e}")

def create_emotion_grid_visualization(original_images, depth_maps, emotions, 
                                     output_path="emotion_depth_grid.png", 
                                     samples_per_emotion=4):
    """Create a grid visualization with samples from each emotion category."""
    if len(original_images) == 0:
        print("No images to visualize")
        return
    
    # Group by emotion
    emotion_groups = {}
    for i, emotion in enumerate(emotions):
        if emotion not in emotion_groups:
            emotion_groups[emotion] = []
        
        original_path = original_images[i]
        depth_path = depth_maps[i] if i < len(depth_maps) and depth_maps[i] else None
        
        if depth_path and os.path.exists(depth_path):
            emotion_groups[emotion].append((original_path, depth_path))
    
    # Get samples for each emotion
    valid_emotions = []
    samples = []
    
    for emotion in sorted(emotion_groups.keys()):
        group_samples = emotion_groups[emotion]
        if len(group_samples) >= samples_per_emotion:
            valid_emotions.append(emotion)
            selected = random.sample(group_samples, samples_per_emotion)
            samples.extend(selected)
    
    if not samples:
        print("No valid samples with both original and depth images found")
        return
    
    # Create grid plot
    num_emotions = len(valid_emotions)
    fig = plt.figure(figsize=(samples_per_emotion*3, num_emotions*4))
    gs = gridspec.GridSpec(num_emotions, samples_per_emotion)
    
    # Add samples for each emotion
    for e_idx, emotion in enumerate(valid_emotions):
        # Add emotion label
        ax = plt.subplot(gs[e_idx, 0])
        ax.text(0, 0.5, emotion.capitalize(), fontsize=14, weight='bold', 
                ha='right', va='center', transform=ax.transAxes)
        ax.axis('off')
        
        # Add samples for this emotion
        for s_idx in range(samples_per_emotion):
            sample_idx = e_idx * samples_per_emotion + s_idx
            if sample_idx < len(samples):
                orig_path, depth_path = samples[sample_idx]
                
                # Create sample grid
                inner_gs = gridspec.GridSpecFromSubplotSpec(2, 1, subplot_spec=gs[e_idx, s_idx], height_ratios=[1, 1])
                
                # Original image
                ax_orig = plt.subplot(inner_gs[0])
                img_orig = Image.open(orig_path).convert('RGB')
                ax_orig.imshow(img_orig)
                ax_orig.set_title("Original", fontsize=10)
                ax_orig.axis('off')
                
                # Depth map
                ax_depth = plt.subplot(inner_gs[1])
                img_depth = Image.open(depth_path).convert('L')
                ax_depth.imshow(img_depth, cmap='viridis')
                ax_depth.set_title("Depth", fontsize=10)
                ax_depth.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Created grid visualization at {output_path}")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Match texture images with depth maps and visualize them in emotion space.")
    parser.add_argument("--high_confidence_file", default="results/high_confidence_images.txt", 
                        help="Path to file with high confidence image paths")
    parser.add_argument("--depth_maps_dir", default="results/depth_maps", 
                        help="Directory containing depth maps")
    parser.add_argument("--classification_file", default="results/classification_results.txt", 
                        help="Path to classification results file (optional)")
    parser.add_argument("--output_dir", default="results", 
                        help="Directory to save visualizations")
    parser.add_argument("--max_samples", type=int, default=500, 
                        help="Maximum number of samples to process (for speed)")
    parser.add_argument("--gallery_samples_per_emotion", type=int, default=20, 
                        help="Maximum samples per emotion in gallery")
    parser.add_argument("--grid_samples_per_emotion", type=int, default=4, 
                        help="Samples per emotion in grid visualization")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("Loading high confidence images...")
    high_conf_images = load_high_confidence_images(args.high_confidence_file)
    if not high_conf_images:
        print("Error: No high confidence images found.")
        return
    
    print(f"Found {len(high_conf_images)} high confidence images.")
    
    # Limit samples if needed
    if args.max_samples and len(high_conf_images) > args.max_samples:
        print(f"Limiting to {args.max_samples} samples for processing speed.")
        high_conf_images = random.sample(high_conf_images, args.max_samples)
    
    # Match original images with depth maps
    print("Matching original images with depth maps...")
    depth_maps = []
    
    for img_path in tqdm(high_conf_images):
        category, filename = extract_image_info(img_path)
        if category and filename:
            depth_map = find_matching_depth_map(category, filename, args.depth_maps_dir)
            depth_maps.append(depth_map)
        else:
            depth_maps.append(None)
    
    valid_pairs = sum(1 for d in depth_maps if d is not None and os.path.exists(d))
    print(f"Found {valid_pairs} valid image-depth map pairs out of {len(high_conf_images)} images.")
    
    # Get emotion classifications
    emotions = []
    confidences = []
    
    if os.path.exists(args.classification_file):
        print(f"Extracting emotions from classification file: {args.classification_file}")
        for img_path in tqdm(high_conf_images, desc="Extracting emotions"):
            emotion, confidence = extract_emotion_from_classifications(img_path, args.classification_file)
            if emotion is None:
                # Try to extract from filename as fallback
                category, _ = extract_image_info(img_path)
                if category:
                    emotions.append(category)
                    confidences.append(0.5)  # Default confidence
                else:
                    emotions.append("unknown")
                    confidences.append(0.0)
            else:
                emotions.append(emotion)
                confidences.append(confidence)
    else:
        print("Classification file not found. Classifying images directly...")
        classifications = classify_images_directly(high_conf_images)
        for img_path in high_conf_images:
            if img_path in classifications:
                emotion, confidence = classifications[img_path]
                emotions.append(emotion)
                confidences.append(confidence)
            else:
                # Use category as fallback
                category, _ = extract_image_info(img_path)
                if category:
                    emotions.append(category)
                    confidences.append(0.5)
                else:
                    emotions.append("unknown")
                    confidences.append(0.0)
    
    print(f"Processed {len(emotions)} images with emotion labels.")
    
    # Create t-SNE visualization
    print("Extracting features for visualization...")
    image_features = create_image_features(high_conf_images)
    depth_features = create_depth_map_features([d for d in depth_maps if d is not None and os.path.exists(d)])
    
    # Only use images that have both features (original+depth)
    valid_indices = [i for i, d in enumerate(depth_maps) if d is not None and os.path.exists(d)]
    
    if valid_indices:
        valid_image_features = image_features[valid_indices]
        valid_emotions = [emotions[i] for i in valid_indices]
        
        combined_features = create_combined_features(valid_image_features, depth_features)
        
        tsne_path = os.path.join(args.output_dir, "emotion_depth_tsne.png")
        print(f"Creating t-SNE visualization with {len(valid_indices)} pairs...")
        create_tsne_visualization(combined_features, valid_emotions, output_path=tsne_path)
    else:
        print("Warning: No valid image-depth pairs for t-SNE visualization.")
    
    # Create gallery visualization
    gallery_path = os.path.join(args.output_dir, "emotion_depth_gallery.html")
    print("Creating gallery visualization...")
    create_gallery_visualization(high_conf_images, depth_maps, emotions, confidences, 
                              output_path=gallery_path,
                              max_samples=args.gallery_samples_per_emotion)
    
    # Create grid visualization if we have valid pairs
    if valid_indices:
        grid_path = os.path.join(args.output_dir, "emotion_depth_grid.png")
        print("Creating grid visualization...")
        valid_originals = [high_conf_images[i] for i in valid_indices]
        valid_depths = [depth_maps[i] for i in valid_indices]
        valid_emotions = [emotions[i] for i in valid_indices]
        create_emotion_grid_visualization(valid_originals, valid_depths, valid_emotions,
                                        output_path=grid_path,
                                        samples_per_emotion=args.grid_samples_per_emotion)
    
    print("Evaluation complete! Visualizations saved to:", args.output_dir)
    print(f"- t-SNE Visualization: {os.path.abspath(tsne_path)}")
    print(f"- Gallery: {os.path.abspath(gallery_path)}")
    if valid_indices:
        print(f"- Grid: {os.path.abspath(grid_path)}")

if __name__ == "__main__":
    main() 