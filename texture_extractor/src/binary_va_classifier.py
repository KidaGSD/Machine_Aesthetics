import os
import torch
import sys
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms
from tqdm import tqdm
import importlib
import subprocess
import random
from pathlib import Path
import seaborn as sns
import argparse

# Ensure the src directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# --- Binary VA Classification Constants ---

# Define the binary VA texture descriptors
BINARY_VA_DESCRIPTORS = {
    "high_valence": [
        # General high valence descriptors - expanded for better representation
        "positive", "pleasant", "appealing", "attractive", "desirable",
        "harmonious", "balanced", "elegant", "beautiful", "refined",
        "inviting", "comfortable", "comforting", "pleasing", "satisfying",
        "welcoming", "cheerful", "bright", "joyful", "uplifting",
        
        # High valence, high arousal specific - enriched descriptors
        "vibrant", "dynamic", "stimulating", "lively", "exciting", "energizing",
        "glossy", "sparkling", "shiny", "reflective", "polished", "glittering",
        "invigorating", "refreshing", "thrilling", "exuberant", "radiant", "luminous",
        
        # High valence, low arousal specific - expanded for better coverage
        "smooth", "soft", "gentle", "soothing", "velvety", "silky", "satiny",
        "plush", "cushioned", "supple", "tender", "comforting", "rounded",
        "serene", "tranquil", "peaceful", "relaxing", "calm", "restful"
    ],
    
    "low_valence": [
        # General low valence descriptors (kept similar)
        "negative", "unpleasant", "unappealing", "unattractive", "undesirable",
        "disharmonious", "unbalanced", "ugly", "crude", "distorted",
        
        # Low valence, high arousal specific
        "rough", "spiky", "abrasive", "chaotic", "jagged", "prickly", "irritating",
        "gritty", "coarse", "scratchy", "harsh", "bristly", "uncomfortable",
        
        # Low valence, low arousal specific
        "dull", "flat", "lifeless", "monotonous", "bland", "boring", "matte",
        "dry", "stale", "faded", "dreary", "plain", "unfinished"
    ],
    
    "high_arousal": [
        # General high arousal descriptors (enriched)
        "energetic", "active", "dynamic", "vibrant", "intense",
        "stimulating", "exciting", "bold", "strong", "powerful",
        "invigorating", "animated", "vigorous", "forceful", "passionate",
        
        # High valence, high arousal specific (enriched)
        "lively", "animated", "vigorous", "exuberant", "expressive",
        "shimmering", "glowing", "radiant", "brilliant", "dramatic",
        "sparkling", "dazzling", "energizing", "vivid", "colorful",
        
        # Low valence, high arousal specific
        "rough", "spiky", "abrasive", "chaotic", "jagged", "prickly", "sharp",
        "tense", "aggressive", "irritating", "uncomfortable", "disturbing"
    ],
    
    "low_arousal": [
        # General low arousal descriptors
        "calm", "passive", "static", "quiet", "gentle",
        "relaxing", "soothing", "subtle", "soft", "delicate",
        
        # High valence, low arousal specific (enriched)
        "smooth", "velvety", "silky", "satiny", "plush", "cushioned", 
        "supple", "tender", "comforting", "rounded", "polished",
        "tranquil", "peaceful", "serene", "balanced", "harmonious",
        
        # Low valence, low arousal specific
        "dull", "flat", "lifeless", "monotonous", "bland", "boring", "matte",
        "dry", "stale", "faded", "dreary", "plain", "unfinished"
    ]
}

# Add quadrant-specific descriptors (Refined for potentially better visual grounding)
QUADRANT_DESCRIPTORS = {
    "high_high": { # High Valence, High Arousal (Exciting, Vibrant, Glossy)
        "descriptors": ["vibrant", "bright", "dazzling", "energetic", 
                      "exuberant", "brilliant", "eye-catching", "striking", "luminous", "radiant",
                      "dynamic", "sparkling", "gleaming", "colorful", "playful", "cheerful"],
        "examples": ["polished chrome", "crystal chandelier", "sparkling water", "glitter", "diamond surface",
                    "freshly waxed car", "vibrant coral reef", "holiday decorations", "prismatic glass"],
        "emotions": ["exhilaration", "excitement", "thrill", "amazement", "joy",
                    "delight", "enthusiasm", "fascination", "awe", "wonder"],
        "opposites": ["dull", "lifeless", "boring", "flat", "mundane", 
                     "lackluster", "dreary", "gloomy", "monotonous", "faded"]
    },
    "high_low": {  # High Valence, Low Arousal (Smooth, Soft, Calm)
        "descriptors": ["smooth", "balanced", "soft", "gentle", 
                      "warm", "serene", "harmonious", "refined", "premium", "elegant",
                      "velvety", "silky", "soothing", "plush", "comforting", "tranquil"],
        "examples": ["cashmere", "fine silk", "polished marble", "premium leather", "satin sheets",
                    "smooth stone", "calm lake surface", "brushed suede", "merino wool", "soft clouds"],
        "emotions": ["relaxation", "contentment", "satisfaction", "tranquility", "comfort",
                    "peace", "serenity", "calmness", "wellness", "relief"],
        "opposites": ["rough", "harsh", "abrasive", "chaotic", "jarring",
                     "unsettling", "agitating", "irregular", "discordant", "uncomfortable"]
    },
    "low_high": {  # Low Valence, High Arousal (Rough, Chaotic, Sharp)
        "descriptors": ["rough", "jagged", "spiky", "abrasive", 
                      "chaotic", "grating", "disruptive", "sharp", "irregular", "coarse",
                      "harsh", "prickly", "uneven", "bristly", "aggressive", "erratic"],
        "examples": ["broken glass", "rusted metal", "thorny cactus", "barbed wire", "rough sandpaper",
                    "cracked concrete", "spiky sea urchin", "pointed rocks", "sharp coral"],
        "emotions": ["anxiety", "fear", "distress", "agitation", "discomfort",
                    "unease", "tension", "alarm", "dread", "nervousness"],
        "opposites": ["smooth", "gentle", "balanced", "orderly", "comfortable",
                     "soft", "pleasant", "harmless", "even", "refined"]
    },
    "low_low": {  # Low Valence, Low Arousal (Dull, Flat, Matte)
        "descriptors": ["lifeless", "plain", "dull", "mundane", 
                      "faded", "bland", "monotonous", "unremarkable", "featureless", "dreary",
                      "muted", "worn", "tired", "flat", "uninspiring", "gloomy"],
        "examples": ["worn cardboard", "dirty concrete", "stained ceiling tile", "old eraser", "cracked plaster",
                    "dusty surface", "weathered fence", "stale bread", "dried mud", "faded fabric"],
        "emotions": ["boredom", "emptiness", "detachment", "numbness", "melancholy",
                    "apathy", "indifference", "weariness", "lethargy", "dullness"],
        "opposites": ["vibrant", "interesting", "lively", "textured", "dynamic",
                     "stimulating", "engaging", "fascinating", "detailed", "rich"]
    }
}

# Template for CLIP prompts
PROMPT_TEMPLATES = [
    "A texture that is {descriptor}",
    "A {descriptor} texture that catches attention",
    "A surface with {descriptor} qualities",
    "A {descriptor} surface texture",
    "Material that feels {descriptor} to the touch",
    "Texture with {descriptor} tactile properties",
    "Surface that looks {descriptor} and invites touching",
    "A {descriptor} textural quality",
    "A texture that shows {descriptor} characteristics",
    "An example of a {descriptor} surface"
]

# Add contrast-based prompts
CONTRAST_TEMPLATES = [
    "A texture that is {descriptor} rather than {opposite}",
    "A distinctly {descriptor} surface, not at all {opposite}",
    "Material that feels {descriptor} instead of {opposite}",
    "Texture with {descriptor} qualities, completely unlike {opposite} surfaces"
]

# Add example-based prompts
EXAMPLE_TEMPLATES = [
    "Texture that looks exactly like {example}",
    "Surface with the exact qualities of {example}",
    "Material that perfectly resembles {example}",
    "A texture indistinguishable from {example}"
]

# Add emotion-based prompts
EMOTION_TEMPLATES = [
    "Texture that immediately evokes a feeling of {emotion}",
    "Surface that makes people feel strong {emotion}",
    "Material texture that intensely triggers {emotion}",
    "A texture that is guaranteed to cause {emotion}"
]

# --- CLIP Related Functions ---

_clip_module = None
def import_clip():
    """Import CLIP module safely, caching the result."""
    global _clip_module
    if _clip_module:
        return _clip_module
    try:
        _clip_module = importlib.import_module('clip')
        print(f"CLIP imported from: {_clip_module.__file__}")
        return _clip_module
    except ImportError:
        print("CLIP module not found. Attempting to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/openai/CLIP.git"])
            print("CLIP installation complete. Importing again...")
            importlib.invalidate_caches()
            _clip_module = importlib.import_module('clip')
            return _clip_module
        except Exception as e:
            print(f"Failed to install or import CLIP: {e}")
            return None

def load_clip_model(device_pref=None):
    """Load the CLIP model."""
    clip = import_clip()
    if clip is None:
        raise ImportError("Could not import or install CLIP module.")
    
    if device_pref:
        device = torch.device(device_pref)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    try:
        # Ensure model is loaded to the correct device from the start
        # Changed from ViT-B/32 to ViT-L/14 for better performance
        model, preprocess = clip.load("ViT-L/14", device=device) 
        print(f"CLIP model loaded: ViT-L/14. Using device: {device}")
        return model, preprocess, device
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        # Try falling back to ViT-B/32 if L/14 fails
        try:
            print("Falling back to ViT-B/32...")
            model, preprocess = clip.load("ViT-B/32", device=device)
            print(f"Fallback CLIP model loaded: ViT-B/32. Using device: {device}")
            return model, preprocess, device
        except:
            raise ImportError("Could not load any CLIP model")

# --- Binary VA Classification Functions ---

def generate_descriptor_prompts(descriptor_list, num_prompts=3):
    """
    Generate text prompts for CLIP using the descriptor list.
    
    Args:
        descriptor_list: List of descriptive words/phrases
        num_prompts: Number of prompts to generate per descriptor
        
    Returns:
        List of generated prompts
    """
    prompts = []
    
    # Ensure we don't try to generate more prompts than templates
    max_templates = min(num_prompts, len(PROMPT_TEMPLATES))
    
    for descriptor in descriptor_list:
        # Select random templates without replacement
        selected_templates = random.sample(PROMPT_TEMPLATES, max_templates)
        
        # Generate prompts with each template
        for template in selected_templates:
            prompt = template.format(descriptor=descriptor)
            prompts.append(prompt)
    
    return prompts

def prepare_text_features(model, text_prompts, device):
    """Encode the text prompts for CLIP.""" 
    clip = import_clip()
    if clip is None:
        raise ImportError("CLIP module not available for tokenization.")
    
    text_inputs = torch.cat([clip.tokenize(prompt) for prompt in text_prompts]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_inputs)
    text_features /= text_features.norm(dim=-1, keepdim=True)
    return text_features

def find_images(input_dir):
    """Find all image files in the input directory (including subdirectories)."""
    image_paths = []
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
    print(f"Scanning directory for images: {input_dir}")
    for root, _, files in os.walk(input_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_paths.append(os.path.abspath(os.path.join(root, file)))
    print(f"Found {len(image_paths)} images.")
    return image_paths

def classify_images_binary_va(model, preprocess, device, image_paths, 
                             high_valence_features, low_valence_features,
                             high_arousal_features, low_arousal_features,
                             valence_bias=0.05):
    """
    Classify images using CLIP for binary VA classification.
    
    Args:
        model: CLIP model
        preprocess: CLIP preprocessing function
        device: Torch device
        image_paths: List of image paths to classify
        high_valence_features: Encoded high valence text features
        low_valence_features: Encoded low valence text features
        high_arousal_features: Encoded high arousal text features
        low_arousal_features: Encoded low arousal text features
        valence_bias: Bias value to shift valence classifications (positive value favors high valence)
        
    Returns:
        Dataframe with classification results
    """
    results = []
    model.eval()
    
    # Process images in batches
    batch_size = 32
    
    print(f"Analyzing {len(image_paths)} images for binary VA classification...")
    print(f"Using valence bias: {valence_bias} to counter classification imbalance")
    
    for i in tqdm(range(0, len(image_paths), batch_size), desc="Classifying Images"):
        batch_paths = image_paths[i:i+batch_size]
        batch_images = []
        valid_paths_in_batch = []

        # Preprocess images in the batch
        for image_path in batch_paths:
            try:
                image = Image.open(image_path).convert("RGB")
                processed_image = preprocess(image)
                batch_images.append(processed_image)
                valid_paths_in_batch.append(image_path)
            except Exception as e:
                print(f"Warning: Skipping image {image_path} due to error: {e}")
        
        if not batch_images:
            continue

        # Stack images into a batch tensor
        image_input = torch.stack(batch_images).to(device)
        
        # Perform inference
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
            # Calculate similarity with each VA dimension
            high_valence_similarity = (image_features @ high_valence_features.T).mean(dim=1)
            low_valence_similarity = (image_features @ low_valence_features.T).mean(dim=1)
            high_arousal_similarity = (image_features @ high_arousal_features.T).mean(dim=1)
            low_arousal_similarity = (image_features @ low_arousal_features.T).mean(dim=1)
            
        # Process results for each image in the batch
        high_valence_cpu = high_valence_similarity.cpu().numpy()
        low_valence_cpu = low_valence_similarity.cpu().numpy()
        high_arousal_cpu = high_arousal_similarity.cpu().numpy()
        low_arousal_cpu = low_arousal_similarity.cpu().numpy()
        
        for j, image_path in enumerate(valid_paths_in_batch):
            # Apply valence bias to address the imbalance toward low valence
            # This increases high_valence scores by the bias amount
            high_v_score = high_valence_cpu[j] + valence_bias
            low_v_score = low_valence_cpu[j]
            
            # Calculate differential scores with the bias included
            valence_score = high_v_score - low_v_score
            
            # Arousal score calculation remains unchanged
            high_a_score = high_arousal_cpu[j]
            low_a_score = low_arousal_cpu[j]
            arousal_score = high_a_score - low_a_score
            
            # Get relative path for cleaner display
            rel_path = os.path.basename(image_path)
            category = os.path.basename(os.path.dirname(image_path))
            
            results.append({
                "image_path": image_path,
                "category": category,
                "filename": rel_path,
                "valence_score": float(valence_score),
                "arousal_score": float(arousal_score),
                "high_valence": float(high_v_score),  # Store biased value for transparency
                "low_valence": float(low_v_score),
                "high_arousal": float(high_a_score),
                "low_arousal": float(low_a_score),
                "valence_bias_applied": float(valence_bias)  # Store the applied bias for reference
            })
    
    # Convert to dataframe
    df_results = pd.DataFrame(results)
    
    # Add quadrant classification
    df_results['valence_class'] = df_results['valence_score'].apply(lambda x: 'high' if x > 0 else 'low')
    df_results['arousal_class'] = df_results['arousal_score'].apply(lambda x: 'high' if x > 0 else 'low')
    df_results['quadrant'] = df_results['valence_class'] + '_' + df_results['arousal_class']
    
    # Normalize scores to [-1, 1] range for better interpretability
    # Enhanced normalization that ensures better distribution:
    # 1. Calculate standard deviation and mean for each dimension
    valence_std = df_results['valence_score'].std()
    arousal_std = df_results['arousal_score'].std()
    valence_mean = df_results['valence_score'].mean()
    arousal_mean = df_results['arousal_score'].mean()
    
    # 2. Z-score normalization (subtract mean, divide by std)
    df_results['valence_z'] = (df_results['valence_score'] - valence_mean) / valence_std
    df_results['arousal_z'] = (df_results['arousal_score'] - arousal_mean) / arousal_std
    
    # 3. Scale to [-1, 1] range, but use a scaling factor that preserves more values in the middle range
    scale_to_range = lambda x: np.clip(x / 2.5, -1, 1)  # Dividing by 2.5 instead of 3 to spread values more
    df_results['valence_normalized'] = df_results['valence_z'].apply(scale_to_range)
    df_results['arousal_normalized'] = df_results['arousal_z'].apply(scale_to_range)
    
    # Log distribution statistics
    print(f"\nValence-Arousal Distribution Statistics:")
    print(f"Valence - Mean: {valence_mean:.4f}, Std: {valence_std:.4f}")
    print(f"Arousal - Mean: {arousal_mean:.4f}, Std: {arousal_std:.4f}")
    print(f"Quadrant Distribution:")
    quadrant_counts = df_results['quadrant'].value_counts()
    for quadrant, count in quadrant_counts.items():
        percentage = (count / len(df_results)) * 100
        print(f"  {quadrant}: {count} images ({percentage:.1f}%)")
    
    return df_results

def visualize_va_distribution(results_df, output_path, title=None, show_categories=True):
    """
    Create a 2D scatter plot visualization of images in the VA space.
    
    Args:
        results_df: DataFrame with classification results
        output_path: Path to save the visualization
        title: Custom title for the plot
        show_categories: Whether to color-code by categories
    """
    plt.figure(figsize=(12, 10))
    
    # Set up the plot
    if show_categories and 'category' in results_df.columns:
        # Color by category
        categories = results_df['category'].unique()
        palette = sns.color_palette("husl", len(categories))
        category_color_map = dict(zip(categories, palette))
        
        for category, group in results_df.groupby('category'):
            plt.scatter(
                group['valence_normalized'], 
                group['arousal_normalized'],
                label=category,
                color=category_color_map[category],
                alpha=0.7,
                edgecolors='w',
                s=50
            )
        plt.legend(title="Texture Categories", bbox_to_anchor=(1.05, 1), loc='upper left')
    else:
        # Color by quadrant
        quadrant_colors = {
            'high_high': 'green',
            'high_low': 'blue',
            'low_high': 'red',
            'low_low': 'purple'
        }
        
        for quadrant, group in results_df.groupby('quadrant'):
            plt.scatter(
                group['valence_normalized'], 
                group['arousal_normalized'],
                label=quadrant.replace('_', ' '),
                color=quadrant_colors.get(quadrant, 'gray'),
                alpha=0.7,
                edgecolors='w',
                s=50
            )
        plt.legend(title="VA Quadrants", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add quadrant separators
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    plt.axvline(x=0, color='black', linestyle='-', alpha=0.3)
    
    # Add quadrant labels
    plt.text(0.85, 0.85, "High Valence\nHigh Arousal", ha='center', fontsize=12)
    plt.text(-0.85, 0.85, "Low Valence\nHigh Arousal", ha='center', fontsize=12)
    plt.text(0.85, -0.85, "High Valence\nLow Arousal", ha='center', fontsize=12)
    plt.text(-0.85, -0.85, "Low Valence\nLow Arousal", ha='center', fontsize=12)
    
    # Set labels and title
    plt.xlabel("Valence (Negative ← → Positive)", fontsize=14)
    plt.ylabel("Arousal (Calm ← → Energetic)", fontsize=14)
    if title:
        plt.title(title, fontsize=16)
    else:
        plt.title("Texture Distribution in Valence-Arousal Space", fontsize=16)
    
    # Set axis limits
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)
    
    # Add grid
    plt.grid(True, linestyle='--', alpha=0.3)
    
    # Save the visualization
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to: {output_path}")
    
    return plt

def save_detailed_results(results_df, output_csv_path, output_stats_path):
    """
    Save detailed results to CSV and generate statistics.
    
    Args:
        results_df: DataFrame with classification results
        output_csv_path: Path to save CSV results
        output_stats_path: Path to save statistics text file
    """
    # Save to CSV
    results_df.to_csv(output_csv_path, index=False)
    print(f"Detailed results saved to: {output_csv_path}")
    
    # Generate statistics
    with open(output_stats_path, 'w') as f:
        f.write("Binary VA Classification Statistics\n")
        f.write("=================================\n\n")
        
        # Overall stats
        f.write(f"Total images analyzed: {len(results_df)}\n\n")
        
        # Quadrant distribution
        f.write("Quadrant Distribution:\n")
        quadrant_counts = results_df['quadrant'].value_counts()
        for quadrant, count in quadrant_counts.items():
            percentage = (count / len(results_df)) * 100
            f.write(f"  {quadrant}: {count} images ({percentage:.1f}%)\n")
        f.write("\n")
        
        # Category distribution (if available)
        if 'category' in results_df.columns:
            f.write("Category Distribution:\n")
            category_counts = results_df['category'].value_counts()
            for category, count in category_counts.items():
                percentage = (count / len(results_df)) * 100
                f.write(f"  {category}: {count} images ({percentage:.1f}%)\n")
            f.write("\n")
        
        # Score ranges
        f.write("Score Ranges:\n")
        f.write(f"  Valence: {results_df['valence_score'].min():.4f} to {results_df['valence_score'].max():.4f}\n")
        f.write(f"  Arousal: {results_df['arousal_score'].min():.4f} to {results_df['arousal_score'].max():.4f}\n\n")
        
        # Most extreme examples
        f.write("Most Positive Valence:\n")
        most_positive = results_df.loc[results_df['valence_score'].idxmax()]
        f.write(f"  {most_positive['filename']} (score: {most_positive['valence_score']:.4f})\n\n")
        
        f.write("Most Negative Valence:\n")
        most_negative = results_df.loc[results_df['valence_score'].idxmin()]
        f.write(f"  {most_negative['filename']} (score: {most_negative['valence_score']:.4f})\n\n")
        
        f.write("Highest Arousal:\n")
        highest_arousal = results_df.loc[results_df['arousal_score'].idxmax()]
        f.write(f"  {highest_arousal['filename']} (score: {highest_arousal['arousal_score']:.4f})\n\n")
        
        f.write("Lowest Arousal:\n")
        lowest_arousal = results_df.loc[results_df['arousal_score'].idxmin()]
        f.write(f"  {lowest_arousal['filename']} (score: {lowest_arousal['arousal_score']:.4f})\n\n")
    
    print(f"Statistics saved to: {output_stats_path}")
    
    return True

def create_sample_grid(results_df, image_dir, output_path, samples_per_quadrant=3):
    """
    Create a grid of sample images from each quadrant.
    
    Args:
        results_df: DataFrame with classification results
        image_dir: Base directory for images (for relative path resolution)
        output_path: Path to save the visualization
        samples_per_quadrant: Number of samples to show per quadrant
    """
    # Define the quadrants
    quadrants = ['high_high', 'high_low', 'low_high', 'low_low']
    quadrant_labels = {
        'high_high': 'High Valence, High Arousal',
        'high_low': 'High Valence, Low Arousal',
        'low_high': 'Low Valence, High Arousal',
        'low_low': 'Low Valence, Low Arousal'
    }
    
    # Create a figure with subplots
    fig, axs = plt.subplots(len(quadrants), samples_per_quadrant, 
                          figsize=(4*samples_per_quadrant, 4*len(quadrants)))
    
    # For each quadrant, select representative samples
    for i, quadrant in enumerate(quadrants):
        # Filter by quadrant and sort by distance from origin
        quadrant_df = results_df[results_df['quadrant'] == quadrant].copy()
        
        if len(quadrant_df) == 0:
            for j in range(samples_per_quadrant):
                axs[i, j].text(0.5, 0.5, f"No images in\n{quadrant_labels[quadrant]}", 
                             ha='center', va='center')
                axs[i, j].axis('off')
            continue
        
        # Calculate distance from quadrant center
        quadrant_df['distance'] = np.sqrt(
            quadrant_df['valence_normalized'].apply(lambda x: (x - (0.5 if 'high' in quadrant else -0.5))**2) + 
            quadrant_df['arousal_normalized'].apply(lambda x: (x - (0.5 if 'high' in quadrant.split('_')[1] else -0.5))**2)
        )
        
        # Sort by distance (closest to quadrant center first)
        quadrant_df = quadrant_df.sort_values('distance')
        
        # Select representative samples
        samples = quadrant_df.head(samples_per_quadrant)
        
        # Display each sample
        for j, (_, sample) in enumerate(samples.iterrows()):
            try:
                img = Image.open(sample['image_path']).convert('RGB')
                axs[i, j].imshow(img, cmap='gray' if img.mode == 'L' else None)
                axs[i, j].set_title(f"V: {sample['valence_normalized']:.2f}, A: {sample['arousal_normalized']:.2f}")
                axs[i, j].axis('off')
            except Exception as e:
                print(f"Error displaying image {sample['image_path']}: {e}")
                axs[i, j].text(0.5, 0.5, "Image load error", ha='center', va='center')
                axs[i, j].axis('off')
    
        # Add quadrant label to the first sample
        if samples_per_quadrant > 0:
            axs[i, 0].text(-0.1, 0.5, quadrant_labels[quadrant], 
                         rotation=90, ha='right', va='center', 
                         transform=axs[i, 0].transAxes,
                         fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Sample grid saved to: {output_path}")
    
    return plt

def generate_quadrant_prompts(quadrant, num_prompts=3, use_contrast=True):
    """
    Generate enhanced prompts specifically for a VA quadrant.
    
    Args:
        quadrant: The VA quadrant ('high_high', 'high_low', etc.)
        num_prompts: Number of prompts to generate per descriptor
        use_contrast: Whether to include contrast-based prompts
    
    Returns:
        List of generated prompts
    """
    prompts = []
    
    # Ensure the quadrant exists
    if quadrant not in QUADRANT_DESCRIPTORS:
        return prompts
    
    descriptors = QUADRANT_DESCRIPTORS[quadrant]["descriptors"]
    examples = QUADRANT_DESCRIPTORS[quadrant]["examples"]
    emotions = QUADRANT_DESCRIPTORS[quadrant]["emotions"]
    opposites = QUADRANT_DESCRIPTORS[quadrant]["opposites"]
    
    # Generate descriptor-based prompts
    for descriptor in descriptors:
        # Select random templates without replacement
        selected_templates = random.sample(PROMPT_TEMPLATES, 
                                         min(num_prompts, len(PROMPT_TEMPLATES)))
        for template in selected_templates:
            prompt = template.format(descriptor=descriptor)
            prompts.append(prompt)
    
    # Add example-based prompts using specific templates
    for example in examples:
        selected_templates = random.sample(EXAMPLE_TEMPLATES,
                                         min(2, len(EXAMPLE_TEMPLATES)))
        for template in selected_templates:
            prompt = template.format(example=example)
            prompts.append(prompt)
    
    # Add emotion-based prompts using specific templates
    for emotion in emotions:
        selected_templates = random.sample(EMOTION_TEMPLATES,
                                         min(2, len(EMOTION_TEMPLATES)))
        for template in selected_templates:
            prompt = template.format(emotion=emotion)
            prompts.append(prompt)
    
    # Add contrast-based prompts if enabled
    if use_contrast and opposites:
        for descriptor in random.sample(descriptors, min(5, len(descriptors))):
            opposite = random.choice(opposites)
            selected_templates = random.sample(CONTRAST_TEMPLATES,
                                             min(2, len(CONTRAST_TEMPLATES)))
            for template in selected_templates:
                prompt = template.format(descriptor=descriptor, opposite=opposite)
                prompts.append(prompt)
    
    return prompts

def run_binary_va_classification(input_dirs, output_dir, device_pref=None, 
                                desc_per_dim=10, prompt_per_desc=2, 
                                use_quadrants=True, use_contrast=True,
                                valence_bias=0.05):
    """
    Run the binary VA classification pipeline on multiple directories.
    
    Args:
        input_dirs: List of directories with texture images
        output_dir: Output directory for results and visualizations
        device_pref: Device preference ('cuda', 'cpu', or None)
        desc_per_dim: Number of descriptors to use per dimension
        prompt_per_desc: Number of prompts to generate per descriptor
        use_quadrants: Whether to use quadrant-specific descriptors
        use_contrast: Whether to use contrast-based prompts
        valence_bias: Bias value to shift valence classifications (positive value favors high valence)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Starting Binary VA Texture Classification...")
        print(f"Valence bias factor: {valence_bias} (positive value shifts classifications toward high valence)")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Load CLIP model
        model, preprocess, device = load_clip_model(device_pref)
        
        # 2. Prepare prompts
        if use_quadrants:
            # Use quadrant-specific descriptors and prompts
            print("Using enhanced quadrant-specific descriptors for more distinct classification...")
            
            high_high_prompts = generate_quadrant_prompts('high_high', prompt_per_desc, use_contrast)
            high_low_prompts = generate_quadrant_prompts('high_low', prompt_per_desc, use_contrast)
            low_high_prompts = generate_quadrant_prompts('low_high', prompt_per_desc, use_contrast)
            low_low_prompts = generate_quadrant_prompts('low_low', prompt_per_desc, use_contrast)
            
            # Combine prompts for valence and arousal dimensions
            high_valence_prompts = high_high_prompts + high_low_prompts
            low_valence_prompts = low_high_prompts + low_low_prompts
            high_arousal_prompts = high_high_prompts + low_high_prompts
            low_arousal_prompts = high_low_prompts + low_low_prompts
            
            print(f"Generated {len(high_valence_prompts)} high valence prompts")
            print(f"Generated {len(low_valence_prompts)} low valence prompts")
            print(f"Generated {len(high_arousal_prompts)} high arousal prompts") 
            print(f"Generated {len(low_arousal_prompts)} low arousal prompts")
        else:
            # Sample descriptors from each dimension
            high_valence_desc = random.sample(BINARY_VA_DESCRIPTORS["high_valence"], min(desc_per_dim, len(BINARY_VA_DESCRIPTORS["high_valence"])))
            low_valence_desc = random.sample(BINARY_VA_DESCRIPTORS["low_valence"], min(desc_per_dim, len(BINARY_VA_DESCRIPTORS["low_valence"])))
            high_arousal_desc = random.sample(BINARY_VA_DESCRIPTORS["high_arousal"], min(desc_per_dim, len(BINARY_VA_DESCRIPTORS["high_arousal"])))
            low_arousal_desc = random.sample(BINARY_VA_DESCRIPTORS["low_arousal"], min(desc_per_dim, len(BINARY_VA_DESCRIPTORS["low_arousal"])))
            
            # Generate prompts for each dimension
            print("Generating prompts for each VA dimension...")
            high_valence_prompts = generate_descriptor_prompts(high_valence_desc, prompt_per_desc)
            low_valence_prompts = generate_descriptor_prompts(low_valence_desc, prompt_per_desc)
            high_arousal_prompts = generate_descriptor_prompts(high_arousal_desc, prompt_per_desc)
            low_arousal_prompts = generate_descriptor_prompts(low_arousal_desc, prompt_per_desc)
        
        print(f"Sample high valence prompts: {high_valence_prompts[:2]}")
        print(f"Sample low valence prompts: {low_valence_prompts[:2]}")
        print(f"Sample high arousal prompts: {high_arousal_prompts[:2]}")
        print(f"Sample low arousal prompts: {low_arousal_prompts[:2]}")
        
        # 3. Prepare text features
        print("Encoding text features...")
        high_valence_features = prepare_text_features(model, high_valence_prompts, device)
        low_valence_features = prepare_text_features(model, low_valence_prompts, device)
        high_arousal_features = prepare_text_features(model, high_arousal_prompts, device)
        low_arousal_features = prepare_text_features(model, low_arousal_prompts, device)
        
        # 4. Create lists to store results for each directory
        all_results = []
        
        # 5. Process each input directory
        for input_dir in input_dirs:
            dir_name = os.path.basename(input_dir)
            print(f"\nProcessing directory: {dir_name}...")
            
            # Find images
            image_paths = find_images(input_dir)
            if not image_paths:
                print(f"No images found in {input_dir}. Skipping.")
                continue
            
            # Classify images
            results_df = classify_images_binary_va(
                model, preprocess, device, image_paths,
                high_valence_features, low_valence_features,
                high_arousal_features, low_arousal_features,
                valence_bias=valence_bias
            )
            
            # Add directory info
            results_df['source_dir'] = dir_name
            
            # Save dir-specific results
            dir_output = os.path.join(output_dir, f"va_results_{dir_name}")
            os.makedirs(dir_output, exist_ok=True)
            
            # Save CSV and stats
            save_detailed_results(
                results_df, 
                os.path.join(dir_output, "va_classification.csv"),
                os.path.join(dir_output, "va_statistics.txt")
            )
            
            # Create visualizations
            visualize_va_distribution(
                results_df,
                os.path.join(dir_output, "va_distribution.png"),
                title=f"VA Distribution - {dir_name}",
                show_categories=True
            )
            
            # Create sample grid
            create_sample_grid(
                results_df,
                input_dir,
                os.path.join(dir_output, "va_samples.png")
            )
            
            # Add to combined results
            all_results.append(results_df)
        
        # 6. Combine results from all directories
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            
            # Save combined results
            save_detailed_results(
                combined_df, 
                os.path.join(output_dir, "va_classification_all.csv"),
                os.path.join(output_dir, "va_statistics_all.txt")
            )
            
            # Create combined visualizations
            visualize_va_distribution(
                combined_df,
                os.path.join(output_dir, "va_distribution_all.png"),
                title="VA Distribution - All Textures",
                show_categories=False
            )
            
            # Create combined visualizations with source directories as categories
            visualize_va_distribution(
                combined_df,
                os.path.join(output_dir, "va_distribution_by_source.png"),
                title="VA Distribution by Source Directory",
                show_categories=True
            )
            
            print(f"\nAll processing complete. Results saved to: {output_dir}")
            return True
        else:
            print("No images were processed. Check your input directories.")
            return False
        
    except Exception as e:
        print(f"An error occurred during the binary VA classification: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def parse_args():
    parser = argparse.ArgumentParser(description="Binary VA (Valence-Arousal) Texture Classification")
    parser.add_argument("--input", nargs='+', required=True, 
                      help="Input directories with texture images (can specify multiple)")
    parser.add_argument("--output", default="data/binary_va_classification", 
                      help="Output directory for results")
    parser.add_argument("--device", choices=["cuda", "cpu"], 
                      help="Device preference (cuda/cpu)")
    parser.add_argument("--descriptors", type=int, default=15,
                      help="Number of descriptors to use per dimension")
    parser.add_argument("--prompts", type=int, default=3,
                      help="Number of prompts to generate per descriptor")
    parser.add_argument("--quadrants", action="store_true", default=True,
                      help="Use quadrant-specific descriptors for better distinction")
    parser.add_argument("--use-contrast", action="store_true", default=True,
                      help="Use contrast-based prompts for better differentiation")
    parser.add_argument("--valence-bias", type=float, default=0.05,
                      help="Bias value to shift classifications toward high valence (default: 0.05)")
    
    return parser.parse_args()

# Main execution
if __name__ == "__main__":
    args = parse_args()
    
    success = run_binary_va_classification(
        input_dirs=args.input,
        output_dir=args.output,
        device_pref=args.device,
        desc_per_dim=args.descriptors,
        prompt_per_desc=args.prompts,
        use_quadrants=args.quadrants,
        use_contrast=args.use_contrast,
        valence_bias=args.valence_bias
    )
    
    sys.exit(0 if success else 1)
