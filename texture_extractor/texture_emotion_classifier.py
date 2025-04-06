import os
import torch
import sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms
from sklearn.metrics import confusion_matrix
import seaborn as sns
from tqdm import tqdm
import importlib
import subprocess
import argparse

# Define the emotions we want to classify
emotions = [
    "joyful", 
    "peaceful", 
    "serene", 
    "anxious", 
    "angry", 
    "sad", 
    "fearful", 
    "disgusted", 
    "surprised", 
    "excited"
]

# DTD-specific categories that map to emotions
dtd_categories = {
    "joyful": ["dotted", "spotted", "sprinkled", "floral", "bright"],
    "peaceful": ["smooth", "plain", "uniform", "monochromatic", "homogeneous"],
    "serene": ["cloudy", "faded", "pale", "soft", "muted"],
    "anxious": ["jagged", "zigzagged", "wavy", "rippled", "wrinkled"],
    "angry": ["bumpy", "knitted", "woven", "braided", "pleated"],
    "sad": ["dotted", "faded", "pale", "muted", "dull"],
    "fearful": ["jagged", "zigzagged", "bumpy", "woven", "braided"],
    "disgusted": ["dotted", "spotted", "sprinkled", "bumpy", "knitted"],
    "surprised": ["floral", "bright", "woven", "braided", "pleated"],
    "excited": ["floral", "bright", "spotted", "sprinkled", "woven"]
}

def import_clip():
    """Import CLIP module safely."""
    try:
        # First attempt to import
        clip = importlib.import_module('clip')
        print(f"CLIP imported from: {clip.__file__}")
        return clip
    except ImportError:
        print("CLIP module not found. Attempting to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/openai/CLIP.git"])
            print("CLIP installation complete. Importing again...")
            importlib.invalidate_caches()  # Clear import cache
            clip = importlib.import_module('clip')
            return clip
        except Exception as e:
            print(f"Failed to install CLIP: {e}")
            print("\nPlease run 'python setup_clip.py' to fix CLIP installation issues.")
            return None

def load_clip_model():
    """Load the CLIP model."""
    # First ensure we have a valid CLIP module
    clip = import_clip()
    if clip is None:
        raise ImportError("Could not import CLIP module. Please run 'python setup_clip.py' first.")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        model, preprocess = clip.load("ViT-B/32", device=device)
        print(f"CLIP model loaded. Using device: {device}")
        return model, preprocess, device
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        print("\nAttempting to verify CLIP installation...")
        
        # Only try to access clip module functions if we have a valid clip module
        if clip:
            print("Available functions in CLIP module:")
            for attr in dir(clip):
                if not attr.startswith('_'):  # Skip private attributes
                    print(f"- {attr}")
        
        print("\nFailed to load CLIP model. Please run 'python setup_clip.py' to fix CLIP installation issues.")
        raise ImportError("Could not load CLIP model")

def prepare_text_features(model, emotions, device, clip_module=None):
    """Encode the emotion text prompts."""
    clip = clip_module or import_clip()
    if clip is None:
        raise ImportError("Could not import CLIP module for text tokenization")
        
    text_inputs = torch.cat([clip.tokenize(f"A texture that feels {emotion}") for emotion in emotions]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_inputs)
    text_features /= text_features.norm(dim=-1, keepdim=True)
    return text_features

def process_image(image_path, preprocess, use_depth=False):
    """Process an image and optionally convert it to a depth map."""
    image = Image.open(image_path).convert("RGB")
    
    if use_depth:
        # Convert to grayscale for depth representation
        image = image.convert("L")
        # Create a pseudo-depth map based on pixel intensity
        image = Image.merge("RGB", [image, image, image])
    
    return preprocess(image)

def classify_images(model, preprocess, text_features, image_paths, device, emotions, use_depth=False):
    """Classify images using CLIP and return results."""
    results = []
    
    for image_path in tqdm(image_paths, desc="Classifying images"):
        image_input = process_image(image_path, preprocess, use_depth)
        image_input = image_input.unsqueeze(0).to(device)
        
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
            # Calculate similarity between image and text features
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
        values, indices = similarity[0].topk(3)
        
        result = {
            "image_path": image_path,
            "top_emotions": [(emotions[idx], values[i].item()) for i, idx in enumerate(indices)]
        }
        results.append(result)
    
    return results

def visualize_results(results, emotions, image_dir):
    """Visualize the classification results."""
    # Count the top emotion for each image
    emotion_counts = {emotion: 0 for emotion in emotions}
    for result in results:
        top_emotion = result["top_emotions"][0][0]
        emotion_counts[top_emotion] += 1
    
    # Create a bar chart
    plt.figure(figsize=(12, 6))
    plt.bar(emotion_counts.keys(), emotion_counts.values())
    plt.xlabel("Emotions")
    plt.ylabel("Count")
    plt.title("Distribution of Emotions in the Dataset")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("emotion_distribution.png")
    plt.close()
    
    # Create a gallery visualization of all images with their emotion tags
    create_image_gallery(results)
    
    print("Visualization completed. Output files:")
    print("- emotion_distribution.png: Bar chart of emotion distribution")
    print("- emotion_gallery.html: Interactive HTML gallery of all images with emotion tags")
    print("- emotion_grid.png: Grid visualization of images with emotion color-coding")

def create_image_gallery(results, max_images=200):
    """Create an HTML gallery of images with their emotion tags."""
    # Limit number of images to prevent huge files
    if len(results) > max_images:
        print(f"Limiting gallery to {max_images} images (out of {len(results)})")
        results = results[:max_images]
    
    # Create HTML content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Texture Emotion Classification Gallery</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                text-align: center;
            }
            .gallery {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                grid-gap: 20px;
                margin-top: 30px;
            }
            .item {
                background: white;
                box-shadow: 0 3px 6px rgba(0,0,0,0.16);
                border-radius: 5px;
                overflow: hidden;
                transition: transform 0.3s;
            }
            .item:hover {
                transform: translateY(-5px);
            }
            .item img {
                width: 100%;
                height: 180px;
                object-fit: cover;
                display: block;
            }
            .emotion {
                padding: 10px;
                font-weight: bold;
                color: #333;
            }
            .score {
                padding: 0 10px 10px;
                color: #666;
                font-size: 0.9em;
            }
            .secondary {
                padding: 0 10px 10px;
                color: #888;
                font-size: 0.8em;
            }
            .joyful { border-top: 4px solid #FFD700; }
            .peaceful { border-top: 4px solid #87CEEB; }
            .serene { border-top: 4px solid #98FB98; }
            .anxious { border-top: 4px solid #FFA07A; }
            .angry { border-top: 4px solid #FF6347; }
            .sad { border-top: 4px solid #6495ED; }
            .fearful { border-top: 4px solid #800080; }
            .disgusted { border-top: 4px solid #8B4513; }
            .surprised { border-top: 4px solid #FF69B4; }
            .excited { border-top: 4px solid #FFA500; }
        </style>
    </head>
    <body>
        <h1>Texture Emotion Classification Gallery</h1>
        <div class="gallery">
    """
    
    # Add each image to the gallery
    for result in results:
        image_path = result["image_path"]
        top_emotion, top_score = result["top_emotions"][0]
        
        # Get file name from path
        file_name = os.path.basename(image_path)
        
        # Add to HTML
        html_content += f"""
        <div class="item {top_emotion}">
            <img src="{image_path}" alt="{file_name}">
            <div class="emotion">{top_emotion.capitalize()}</div>
            <div class="score">Confidence: {top_score:.2f}</div>
            <div class="secondary">
        """
        
        # Add secondary emotions
        for emotion, score in result["top_emotions"][1:]:
            html_content += f"{emotion}: {score:.2f}<br>"
        
        html_content += """
            </div>
        </div>
        """
    
    # Close HTML
    html_content += """
        </div>
    </body>
    </html>
    """
    
    # Write to file
    with open("emotion_gallery.html", "w") as f:
        f.write(html_content)
    
    print(f"Created gallery with {len(results)} images.")
    
    # Create a simpler version as a grid image
    create_image_grid(results)

def create_image_grid(results, max_images=100, grid_size=(10, 10)):
    """Create a grid image showing the classification results."""
    if len(results) > max_images:
        print(f"Limiting grid to {max_images} images (out of {len(results)})")
        results = results[:max_images]
    
    # Determine grid dimensions
    rows, cols = grid_size
    if len(results) < rows * cols:
        # Adjust grid size for fewer images
        cols = min(cols, len(results))
        rows = (len(results) + cols - 1) // cols  # Ceiling division
    
    # Create figure
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2, rows * 2))
    if rows * cols == 1:
        axes = np.array([axes])  # Make it indexable for the loop
    axes = axes.flatten()
    
    # Map emotions to colors for visual identification
    emotion_colors = {
        "joyful": "#FFD700",     # Gold
        "peaceful": "#87CEEB",   # Sky Blue
        "serene": "#98FB98",     # Pale Green
        "anxious": "#FFA07A",    # Light Salmon
        "angry": "#FF6347",      # Tomato
        "sad": "#6495ED",        # Cornflower Blue
        "fearful": "#800080",    # Purple
        "disgusted": "#8B4513",  # Saddle Brown
        "surprised": "#FF69B4",  # Hot Pink
        "excited": "#FFA500"     # Orange
    }
    
    # Fill the grid with images
    for i, result in enumerate(results):
        if i >= len(axes):
            break
            
        # Get the image and emotion
        image_path = result["image_path"]
        top_emotion, top_score = result["top_emotions"][0]
        
        # Load and display the image
        try:
            img = Image.open(image_path).convert("RGB")
            axes[i].imshow(img)
            
            # Add colored border based on emotion
            color = emotion_colors.get(top_emotion, "#333333")
            for spine in axes[i].spines.values():
                spine.set_edgecolor(color)
                spine.set_linewidth(3)
            
            # Set title with emotion and score
            axes[i].set_title(f"{top_emotion}\n{top_score:.2f}", fontsize=8)
            axes[i].axis("off")
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            axes[i].text(0.5, 0.5, "Error loading image", 
                         ha='center', va='center', fontsize=8)
            axes[i].axis("off")
    
    # Hide any unused subplots
    for i in range(len(results), len(axes)):
        axes[i].axis("off")
    
    # Add a legend for emotions and their colors
    legend_elements = [plt.Line2D([0], [0], color=color, lw=4, label=emotion)
                      for emotion, color in emotion_colors.items()]
    fig.legend(handles=legend_elements, loc='upper center', 
               bbox_to_anchor=(0.5, 0.02), ncol=5, fontsize=8)
    
    # Adjust layout and save
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.1)  # Make room for the legend
    plt.savefig("emotion_grid.png", dpi=300)
    plt.close()
    
    print("Created image grid visualization: emotion_grid.png")

def main():
    """Main function to run the emotion classification process."""
    # Get script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Classify texture images using CLIP and optionally filter by confidence.")
    parser.add_argument("--input_dir", default="dtd/images", help="Directory containing input images (default: dtd/images)")
    parser.add_argument("--device", choices=["cuda", "cpu"], default=None, help="Device to use (default: auto-detect)")
    parser.add_argument("--confidence_threshold", type=float, default=0.5, help="Minimum confidence score for the top emotion to include an image (default: 0.5).")
    parser.add_argument("--skip_visualizations", action="store_true", help="Skip generating visualization files (distribution, gallery, grid).")
    
    args = parser.parse_args()
    
    # Resolve input directory path (either absolute or relative to script directory)
    if not os.path.isabs(args.input_dir):
        input_dir = os.path.join(script_dir, args.input_dir)
    else:
        input_dir = args.input_dir
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' doesn't exist")
        return
    
    # Create results directory structure
    results_dir = os.path.join(script_dir, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Default output paths
    output_image_list = os.path.join(results_dir, "high_confidence_images.txt")
    
    # Check if CUDA is available
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    # Import CLIP first
    clip = import_clip()
    if clip is None:
        print("Failed to import CLIP. Please run the setup_clip.py script first.")
        return
        
    # Load the CLIP model
    try:
        model, preprocess, device = load_clip_model()
        # Override device if specified
        if args.device:
            device = torch.device(args.device)
            model.to(device)
            print(f"Overriding device based on argument: using {device}")
        
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    # Prepare text features
    try:
        text_features = prepare_text_features(model, emotions, device, clip)
    except ImportError as e:
        print(f"Error: {e}")
        return
    
    # Get all image files (assuming color images now)
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
    image_paths = []
    
    print(f"Scanning directory: {input_dir}")
    for root, _, files in os.walk(input_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in image_extensions:
                # Make sure path is absolute or consistently relative for later use
                image_paths.append(os.path.abspath(os.path.join(root, file))) 
    
    if not image_paths:
        print(f"No image files found in '{input_dir}'")
        return
    
    print(f"Found {len(image_paths)} images to process.")
    
    # Classify images (always using color images here, use_depth=False)
    results = classify_images(model, preprocess, text_features, image_paths, device, emotions, use_depth=False)
    
    # --- Filtering based on confidence --- 
    filtered_results = []
    filtered_image_paths = []
    if results: # Ensure results is not empty
        for result in results:
             # Check confidence of the top emotion
             if result["top_emotions"] and result["top_emotions"][0][1] >= args.confidence_threshold:
                 filtered_results.append(result)
                 filtered_image_paths.append(result["image_path"])

    print(f"\nFiltered {len(filtered_results)} images with confidence >= {args.confidence_threshold}")

    # --- Save filtered image list --- 
    try:
        with open(output_image_list, "w") as f:
            for img_path in filtered_image_paths:
                f.write(f"{img_path}\n")
        print(f"Saved list of {len(filtered_image_paths)} high-confidence image paths to: {output_image_list}")
    except Exception as e:
        print(f"Error writing filtered image list to {output_image_list}: {e}")

    # --- Optional Visualizations / Save Full Results --- 
    if not args.skip_visualizations:
        # Visualize results (using ALL results, not just filtered, unless you want to change this)
        print("\nGenerating visualizations based on ALL classification results...")
        visualize_results(results, emotions, input_dir)
        
        # Save detailed results to a file (ALL results)
        print("\nSaving full classification results...")
        classification_results_path = os.path.join(results_dir, "classification_results.txt")
        with open(classification_results_path, "w") as f:
            for result in results:
                f.write(f"Image: {result['image_path']}\n")
                top_conf = -1
                for i, (emotion, score) in enumerate(result["top_emotions"]):
                    if i == 0: top_conf = score
                    f.write(f"- {emotion}: {score:.4f}\n")
                    # Add DTD categories that map to this emotion
                    # Check if emotion exists in dtd_categories first
                    if emotion in dtd_categories:
                         f.write(f"  Related DTD categories: {', '.join(dtd_categories[emotion])}\n")
                    else:
                         f.write("  Related DTD categories: N/A\n")
                # Mark if it passed the threshold
                passed = "YES" if top_conf >= args.confidence_threshold else "NO"
                f.write(f"Passed Threshold ({args.confidence_threshold}): {passed}\n")
                f.write("\n")
        print(f"Full classification results saved to {classification_results_path}")
        
        # Save outputs to results directory
        import shutil
        if os.path.exists("emotion_distribution.png"):
            shutil.move("emotion_distribution.png", os.path.join(results_dir, "emotion_distribution.png"))
        if os.path.exists("emotion_gallery.html"):
            shutil.move("emotion_gallery.html", os.path.join(results_dir, "emotion_gallery.html"))
        if os.path.exists("emotion_grid.png"):
            shutil.move("emotion_grid.png", os.path.join(results_dir, "emotion_grid.png"))
            
        print(f"All results saved to '{results_dir}' directory")
    else:
        print("\nSkipping visualizations and detailed results saving.")

if __name__ == "__main__":
    # Need to import torch and os if not already done globally
    import torch 
    import os
    import sys # For setup_clip.py checks
    import importlib # For setup_clip.py checks
    import subprocess # For setup_clip.py checks
    from PIL import Image # For process_image
    from torchvision import transforms # For process_image (though handled by CLIP load)
    from tqdm import tqdm # For classify_images
    import matplotlib.pyplot as plt # For visualize_results
    import seaborn as sns # For visualize_results

    main() 