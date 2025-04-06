import os
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import re
from collections import defaultdict

# Define the same emotions as in the main script
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

def parse_classification_results(results_file):
    """Parse the classification_results.txt file to extract results."""
    results = []
    current_result = None
    
    with open(results_file, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_result and 'top_emotions' in current_result:
                results.append(current_result)
            current_result = None
        elif line.startswith('Image:'):
            current_result = {'image_path': line[6:].strip(), 'top_emotions': []}
        elif line.startswith('- '):
            if current_result:
                parts = line[2:].split(': ')
                if len(parts) == 2:
                    emotion, score = parts
                    current_result['top_emotions'].append((emotion, float(score)))
    
    # Add the last result if the file doesn't end with a blank line
    if current_result and 'top_emotions' in current_result:
        results.append(current_result)
    
    return results

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

def visualize_results(results, emotions):
    """Generate visualizations from parsed results."""
    # Count the top emotion for each image
    emotion_counts = defaultdict(int)
    for result in results:
        top_emotion = result["top_emotions"][0][0]
        emotion_counts[top_emotion] += 1
    
    # Create a bar chart of emotion distribution
    plt.figure(figsize=(12, 6))
    emotions_present = sorted(emotion_counts.keys())
    counts = [emotion_counts[emotion] for emotion in emotions_present]
    
    plt.bar(emotions_present, counts)
    plt.xlabel("Emotions")
    plt.ylabel("Count")
    plt.title("Distribution of Emotions in the Dataset")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("emotion_distribution.png")
    plt.close()
    
    # Create a sample grid showing one example of each emotion
    sample_imgs = {}
    for emotion in emotions:
        for result in results:
            if result["top_emotions"][0][0] == emotion:
                sample_imgs[emotion] = (result["image_path"], result["top_emotions"][0][1])
                break
    
    # If we found examples of emotions, create a sample grid
    if sample_imgs:
        # Determine grid dimensions
        num_emotions = len(sample_imgs)
        cols = min(5, num_emotions)
        rows = (num_emotions + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 4))
        if rows * cols == 1:
            axes = np.array([axes])
        axes = axes.flatten()
        
        for i, (emotion, (img_path, score)) in enumerate(sample_imgs.items()):
            try:
                img = Image.open(img_path).convert("RGB")
                axes[i].imshow(img)
                axes[i].set_title(f"{emotion}: {score:.2f}")
                axes[i].axis("off")
            except Exception as e:
                print(f"Error loading sample image for {emotion}: {e}")
                axes[i].text(0.5, 0.5, f"Error: {emotion}", 
                             ha='center', va='center')
                axes[i].axis("off")
        
        # Hide any unused subplots
        for i in range(num_emotions, len(axes)):
            axes[i].axis("off")
            
        plt.tight_layout()
        plt.savefig("emotion_samples.png")
        plt.close()
        print("Created sample grid: emotion_samples.png")
    
    # Create confidence distribution visualization
    confidence_values = [result["top_emotions"][0][1] for result in results]
    plt.figure(figsize=(10, 6))
    plt.hist(confidence_values, bins=20, alpha=0.7)
    plt.xlabel("Confidence")
    plt.ylabel("Count")
    plt.title("Distribution of Classification Confidence")
    plt.savefig("confidence_distribution.png")
    plt.close()
    
    # Create the gallery and grid visualizations
    create_image_gallery(results)
    create_image_grid(results)
    
    print("\nVisualization completed. Output files:")
    print("- emotion_distribution.png: Bar chart of emotion distribution")
    print("- confidence_distribution.png: Histogram of confidence scores")
    print("- emotion_gallery.html: Interactive HTML gallery of all images with emotion tags")
    print("- emotion_grid.png: Grid visualization of images with emotion color-coding")
    if sample_imgs:
        print("- emotion_samples.png: One example image for each emotion category")

def main():
    results_file = "classification_results.txt"
    
    if not os.path.exists(results_file):
        print(f"Error: {results_file} not found. Please run the classification first or specify the correct path.")
        return
    
    print(f"Parsing classification results from {results_file}...")
    results = parse_classification_results(results_file)
    
    if not results:
        print("No valid results found in the file.")
        return
    
    print(f"Found {len(results)} classified images.")
    visualize_results(results, emotions)

if __name__ == "__main__":
    main() 