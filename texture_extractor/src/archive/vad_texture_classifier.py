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

# Ensure the src directory is in the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Local imports
try:
    # Import the VAD mapping
    from vad_texture_mapping import VAD_TEXTURE_MAPPING
except ImportError:
    # If direct import fails, try to load from JSON
    VAD_TEXTURE_MAPPING = None

# --- VAD Classification Constants ---

# Default threshold values if not loaded from mapping
DEFAULT_VAD_THRESHOLDS = {
    "valence_thresholds": [0.4, 0.6],  # Negative < 0.4 <= Neutral < 0.6 <= Positive
    "arousal_thresholds": [0.4, 0.6],  # Low < 0.4 <= Moderate < 0.6 <= High
    "dominance_threshold": 0.5         # Low < 0.5 <= High
}

# Template for CLIP prompts
PROMPT_TEMPLATES = [
    "A texture that is {descriptor}",
    "A {descriptor} texture",
    "A surface with {descriptor} qualities",
    "{descriptor} material texture"
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
        model, preprocess = clip.load("ViT-B/32", device=device) 
        print(f"CLIP model loaded. Using device: {device}")
        return model, preprocess, device
    except Exception as e:
        print(f"Error loading CLIP model: {e}")
        raise ImportError("Could not load CLIP model")

# --- VAD Classification Functions ---

def load_vad_mapping():
    """Load the VAD-to-texture mapping from configuration."""
    global VAD_TEXTURE_MAPPING
    
    if VAD_TEXTURE_MAPPING is not None:
        return VAD_TEXTURE_MAPPING
    
    # Try to load from JSON if not already imported
    config_path = os.path.join(os.path.dirname(script_dir), "config", "vad_texture_mapping.json")
    try:
        with open(config_path, 'r') as f:
            VAD_TEXTURE_MAPPING = json.load(f)
        print(f"Loaded VAD mapping from: {config_path}")
        return VAD_TEXTURE_MAPPING
    except Exception as e:
        print(f"Warning: Could not load VAD mapping from {config_path}: {e}")
        print("Using default VAD threshold values.")
        return {
            "valence_thresholds": DEFAULT_VAD_THRESHOLDS["valence_thresholds"],
            "arousal_thresholds": DEFAULT_VAD_THRESHOLDS["arousal_thresholds"],
            "dominance_threshold": DEFAULT_VAD_THRESHOLDS["dominance_threshold"],
            "mapping": {},
            "dominance_modifiers": {
                "high": ["bold", "structured", "organized", "strong", "defined"],
                "low": ["fragmented", "scattered", "randomized", "diffuse", "fluid"]
            }
        }

def read_vad_scores(vad_csv_path):
    """
    Read VAD (Valence, Arousal, Dominance) scores from a CSV file.
    
    Args:
        vad_csv_path: Path to the CSV file containing VAD scores
        
    Returns:
        Dictionary with VAD scores or None if file cannot be read
    """
    try:
        # Check if the file exists
        if not os.path.exists(vad_csv_path):
            print(f"Error: VAD CSV file not found: {vad_csv_path}")
            return None
        
        # Determine the CSV format based on columns
        df = pd.read_csv(vad_csv_path)
        
        # Different possible column names for VAD values
        valence_cols = ['Valence', 'valence', 'V']
        arousal_cols = ['Arousal', 'arousal', 'A'] 
        dominance_cols = ['Dominance', 'dominance', 'D']
        
        # Find the correct column names if they exist
        valence_col = next((col for col in valence_cols if col in df.columns), None)
        arousal_col = next((col for col in arousal_cols if col in df.columns), None)
        dominance_col = next((col for col in dominance_cols if col in df.columns), None)
        
        # If we don't have dominance, see if we can derive it
        if dominance_col is None and valence_col is not None and arousal_col is not None:
            print("Dominance score not found. Using mean of valence and arousal as an estimate.")
            dominance = df[valence_col].mean() * 0.7 + df[arousal_col].mean() * 0.3
        elif dominance_col is not None:
            dominance = df[dominance_col].mean()
        else:
            dominance = 0.5  # Default middle value
        
        # If we don't have valence or arousal, we can't proceed
        if valence_col is None or arousal_col is None:
            print(f"Error: Could not find valence and arousal columns in the CSV file.")
            print(f"Available columns: {', '.join(df.columns)}")
            print(f"Expected format: CSV with 'Valence' and 'Arousal' columns.")
            print(f"The VAD classifier requires proper valence-arousal-dominance values.")
            print(f"See vad_texture_mapping.py for details on the VAD mapping.")
            return None
            
        # Get the mean values (if multiple rows exist)
        valence = df[valence_col].mean()
        arousal = df[arousal_col].mean()
        
        return {
            "valence": float(valence),
            "arousal": float(arousal),
            "dominance": float(dominance)
        }
        
    except Exception as e:
        print(f"Error reading VAD CSV file {vad_csv_path}: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def map_vad_to_quadrant(vad_scores, mapping):
    """
    Map VAD scores to a quadrant in the emotion space and select appropriate texture descriptors.
    
    Args:
        vad_scores: Dictionary with valence, arousal, dominance values
        mapping: Dictionary with mapping configurations
        
    Returns:
        Dictionary with quadrant, descriptors, and other information
    """
    valence = vad_scores["valence"]
    arousal = vad_scores["arousal"]
    dominance = vad_scores["dominance"]
    
    # Get thresholds from mapping
    v_thresholds = mapping.get("valence_thresholds", DEFAULT_VAD_THRESHOLDS["valence_thresholds"])
    a_thresholds = mapping.get("arousal_thresholds", DEFAULT_VAD_THRESHOLDS["arousal_thresholds"])
    d_threshold = mapping.get("dominance_threshold", DEFAULT_VAD_THRESHOLDS["dominance_threshold"])
    
    # Determine valence category
    if valence < v_thresholds[0]:
        valence_category = "negative"
    elif valence > v_thresholds[1]:
        valence_category = "positive"
    else:
        valence_category = "neutral"
    
    # Determine arousal category
    if arousal < a_thresholds[0]:
        arousal_category = "low"
    elif arousal > a_thresholds[1]:
        arousal_category = "high"
    else:
        arousal_category = "moderate"
    
    # Determine dominance category
    dominance_category = "high" if dominance > d_threshold else "low"
    
    # Create quadrant key
    quadrant_key = f"{valence_category}_{arousal_category}"
    
    # Get base descriptors for this quadrant
    texture_descriptors = mapping.get("mapping", {}).get(quadrant_key, [])
    if not texture_descriptors:
        print(f"Warning: No texture descriptors found for quadrant {quadrant_key}")
        # Fallback to some default descriptors based on the quadrant
        default_descriptors = {
            "negative_high": ["jagged", "spiky", "chaotic"],
            "negative_moderate": ["somber", "muted", "subdued"],
            "negative_low": ["dull", "flat", "lifeless"],
            "neutral_high": ["dynamic", "geometric", "taut"],
            "neutral_moderate": ["balanced", "moderate", "uniform"],
            "neutral_low": ["blurred", "faded", "gentle"],
            "positive_high": ["energetic", "bright", "bold"],
            "positive_moderate": ["elegant", "warm", "flowing"],
            "positive_low": ["calm", "smooth", "serene"]
        }
        texture_descriptors = default_descriptors.get(quadrant_key, ["neutral", "textured", "patterned"])
    
    # Get dominance modifiers
    dom_modifiers = mapping.get("dominance_modifiers", {}).get(dominance_category, [])
    
    return {
        "quadrant": quadrant_key,
        "valence_category": valence_category,
        "arousal_category": arousal_category,
        "dominance_category": dominance_category,
        "base_descriptors": texture_descriptors,
        "dominance_modifiers": dom_modifiers,
        "vad_scores": vad_scores
    }

def generate_texture_prompts(mapping_result, num_prompts=3, descriptors_per_prompt=2):
    """
    Generate text prompts for texture search using the mapping result.
    
    Args:
        mapping_result: Result from map_vad_to_quadrant
        num_prompts: Number of prompts to generate
        descriptors_per_prompt: Number of descriptors to use per prompt
        
    Returns:
        List of generated prompts
    """
    base_descriptors = mapping_result["base_descriptors"]
    dom_modifiers = mapping_result["dominance_modifiers"]
    
    if not base_descriptors:
        return ["A texture", "A textured surface", "A material texture"]
    
    # Ensure we have enough descriptors
    if len(base_descriptors) < descriptors_per_prompt:
        base_descriptors = base_descriptors * (descriptors_per_prompt // len(base_descriptors) + 1)
    
    # Generate prompts
    prompts = []
    for _ in range(num_prompts):
        # Select random base descriptors
        selected_descriptors = random.sample(base_descriptors, min(descriptors_per_prompt, len(base_descriptors)))
        
        # Add a dominance modifier with 70% probability
        if dom_modifiers and random.random() < 0.7:
            modifier = random.choice(dom_modifiers)
            selected_descriptors.append(modifier)
        
        # Combine descriptors into a single string
        descriptor_string = ", ".join(selected_descriptors)
        
        # Apply a random template
        template = random.choice(PROMPT_TEMPLATES)
        prompt = template.format(descriptor=descriptor_string)
        
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
    """Find all image files in the input directory."""
    image_paths = []
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
    print(f"Scanning directory for images: {input_dir}")
    for root, _, files in os.walk(input_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_paths.append(os.path.abspath(os.path.join(root, file)))
    print(f"Found {len(image_paths)} images.")
    return image_paths

def classify_images_vad(model, preprocess, text_features, image_paths, device, text_prompts):
    """
    Classify images using CLIP based on VAD-generated prompts.
    
    Args:
        model: CLIP model
        preprocess: CLIP preprocessing function
        text_features: Encoded text features
        image_paths: List of image paths to classify
        device: Torch device
        text_prompts: List of text prompts used
        
    Returns:
        List of results with image paths and scores
    """
    results = []
    model.eval()
    
    # Process images in batches
    batch_size = 32
    
    print(f"Classifying {len(image_paths)} images using VAD-based prompts...")
    
    for i in tqdm(range(0, len(image_paths), batch_size), desc="Classifying Batches"):
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
            
            # Calculate similarity with all prompts
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
        # Process results for each image in the batch
        similarity_cpu = similarity.cpu().numpy()
        for j, image_path in enumerate(valid_paths_in_batch):
            scores = similarity_cpu[j]
            
            # For each image, get the mean score across all prompts
            # This represents how well the image matches the overall VAD-based texture concept
            mean_score = np.mean(scores)
            
            # Get individual prompt scores
            prompt_scores = [(text_prompts[idx], scores[idx]) for idx in range(len(text_prompts))]
            
            results.append({
                "image_path": image_path,
                "mean_score": mean_score,
                "prompt_scores": prompt_scores
            })
    
    # Sort results by mean score (highest first)
    results.sort(key=lambda x: x["mean_score"], reverse=True)
    
    return results

def save_vad_results(results, confidence_threshold, output_list_path, output_results_path, vad_info):
    """
    Filter results by confidence and save the list and detailed scores.
    
    Args:
        results: List of classification results
        confidence_threshold: Minimum confidence threshold
        output_list_path: Path to save high-confidence image list
        output_results_path: Path to save detailed results
        vad_info: VAD mapping information
        
    Returns:
        True if successful, False otherwise
    """
    high_confidence_paths = []
    
    print(f"Filtering results with confidence threshold >= {confidence_threshold}")
    
    # Create output directories if needed
    os.makedirs(os.path.dirname(output_list_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_results_path), exist_ok=True)
    
    try:
        with open(output_results_path, "w", encoding='utf-8') as f_details:
            # Write VAD info header
            f_details.write("VAD-Based Texture Classification Results\n")
            f_details.write("======================================\n\n")
            
            f_details.write(f"VAD Scores: Valence={vad_info['vad_scores']['valence']:.4f}, " +
                          f"Arousal={vad_info['vad_scores']['arousal']:.4f}, " +
                          f"Dominance={vad_info['vad_scores']['dominance']:.4f}\n\n")
            
            f_details.write(f"Emotion Quadrant: {vad_info['quadrant'].replace('_', '-').title()}\n")
            f_details.write(f"Dominance Category: {vad_info['dominance_category'].title()}\n\n")
            
            f_details.write("Texture Descriptors Used:\n")
            for desc in vad_info['base_descriptors'][:5]:
                f_details.write(f"- {desc}\n")
            
            f_details.write("\nDominance Modifiers Used:\n")
            for mod in vad_info['dominance_modifiers'][:3]:
                f_details.write(f"- {mod}\n")
            
            f_details.write("\nPrompts Generated:\n")
            prompt_list = [ps[0] for r in results[:1] for ps in r["prompt_scores"]]
            for prompt in prompt_list:
                f_details.write(f"- {prompt}\n")
            
            f_details.write("\n\n")
            f_details.write("Image Classification Results:\n")
            f_details.write("============================\n\n")
            
            # Write individual image results
            for result in results:
                image_path = result["image_path"]
                mean_score = result["mean_score"]
                passed_threshold = mean_score >= confidence_threshold
                
                f_details.write(f"Image: {image_path}\n")
                f_details.write(f"Mean Score: {mean_score:.4f}\n")
                
                # Add top 3 prompt scores
                f_details.write("Top Prompt Matches:\n")
                for prompt, score in result["prompt_scores"][:3]:
                    f_details.write(f"- {prompt}: {score:.4f}\n")
                
                f_details.write(f"Passed Threshold ({confidence_threshold}): {'YES' if passed_threshold else 'NO'}\n\n")
                
                if passed_threshold:
                    high_confidence_paths.append(image_path)
        
        print(f"Saved detailed classification results to: {output_results_path}")
        
    except Exception as e:
        print(f"Error writing detailed results to {output_results_path}: {e}")
        return False
    
    try:
        with open(output_list_path, "w", encoding='utf-8') as f_list:
            for img_path in high_confidence_paths:
                f_list.write(f"{img_path}\n")
        print(f"Saved list of {len(high_confidence_paths)} high-confidence image paths to: {output_list_path}")
    except Exception as e:
        print(f"Error writing high-confidence list to {output_list_path}: {e}")
        return False
    
    return True

def run_vad_classification_pipeline(vad_csv_path, input_dir, confidence_threshold, device_pref, 
                                   output_list_path, output_results_path, is_file_list=False,
                                   num_prompts=5, valence_bias=0.05):
    """
    Run the VAD-based texture classification pipeline.
    
    Args:
        vad_csv_path (str): Path to the CSV file with VAD scores
        input_dir (str): Directory with texture images or file list
        confidence_threshold (float): Minimum confidence score
        device_pref (str): Device preference ('cuda', 'cpu', or None)
        output_list_path (str): Where to save high-confidence images list
        output_results_path (str): Where to save detailed results
        is_file_list (bool): Whether input_dir is a file list
        num_prompts (int): Number of prompts to generate
        valence_bias (float): Bias value to shift classifications toward high valence
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Starting VAD-based texture classification pipeline...")
        print(f"Using valence bias: {valence_bias} to improve classification balance")
        
        # 1. Load the VAD mapping
        mapping = load_vad_mapping()
        if not mapping:
            print("Error: Could not load VAD mapping.")
            return False
        
        # 2. Read VAD scores from CSV
        vad_scores = read_vad_scores(vad_csv_path)
        if not vad_scores:
            print(f"Error: Could not read VAD scores from {vad_csv_path}")
            return False
        
        # Apply valence bias to the VAD scores
        vad_scores['valence'] += valence_bias
        
        print(f"Loaded VAD scores (with bias applied): Valence={vad_scores['valence']:.4f}, " +
             f"Arousal={vad_scores['arousal']:.4f}, Dominance={vad_scores['dominance']:.4f}")
        
        # 3. Map VAD scores to texture descriptors
        vad_mapping = map_vad_to_quadrant(vad_scores, mapping)
        quadrant = vad_mapping["quadrant"]
        print(f"Mapped to quadrant: {quadrant} with dominance: {vad_mapping['dominance_category']}")
        
        # 4. Generate prompts for CLIP
        prompts = generate_texture_prompts(vad_mapping, num_prompts=num_prompts)
        print(f"Generated {len(prompts)} texture prompts:")
        for prompt in prompts:
            print(f"  - {prompt}")
        
        # 5. Load CLIP model
        model, preprocess, device = load_clip_model(device_pref)
        
        # 6. Prepare text features
        text_features = prepare_text_features(model, prompts, device)
        
        # 7. Find images
        if is_file_list:
            try:
                with open(input_dir, 'r') as f:
                    image_paths = [line.strip() for line in f if line.strip()]
                print(f"Read {len(image_paths)} image paths from file: {input_dir}")
            except Exception as e:
                print(f"Error reading image paths from file {input_dir}: {e}")
                return False
        else:
            image_paths = find_images(input_dir)
        
        if not image_paths:
            print("No images found. Exiting.")
            return False
        
        # 8. Classify images
        results = classify_images_vad(model, preprocess, text_features, image_paths, device, prompts)
        
        # 9. Save results
        success = save_vad_results(results, confidence_threshold, output_list_path, 
                                 output_results_path, vad_mapping)
        
        return success
        
    except Exception as e:
        print(f"An error occurred during the VAD classification pipeline: {e}")
        import traceback
        print(traceback.format_exc())
        return False

# This function provides a compatible interface with the original classifier
def run_classification_pipeline(input_dir, confidence_threshold, device_pref, 
                               output_list_path, output_results_path, is_file_list=False,
                               vad_csv_path=None, valence_bias=0.05):
    """
    Compatibility wrapper for the original classifier interface.
    If vad_csv_path is provided, uses VAD-based classification,
    otherwise falls back to the original emotion-based classifier.
    
    Args:
        input_dir (str): Directory with texture images or file list
        confidence_threshold (float): Minimum confidence score
        device_pref (str): Device preference ('cuda', 'cpu', or None)
        output_list_path (str): Where to save high-confidence images list
        output_results_path (str): Where to save detailed results
        is_file_list (bool): Whether input_dir is a file list
        vad_csv_path (str, optional): Path to the CSV file with VAD scores
        valence_bias (float): Bias value to shift classifications toward high valence
        
    Returns:
        bool: True if successful, False otherwise
    """
    if vad_csv_path and os.path.exists(vad_csv_path):
        print(f"Using VAD-based texture classification with scores from: {vad_csv_path}")
        return run_vad_classification_pipeline(
            vad_csv_path=vad_csv_path,
            input_dir=input_dir,
            confidence_threshold=confidence_threshold,
            device_pref=device_pref,
            output_list_path=output_list_path,
            output_results_path=output_results_path,
            is_file_list=is_file_list,
            valence_bias=valence_bias
        )
    else:
        # Fall back to the original classifier
        print("No VAD CSV provided or file not found. Using traditional emotion classifier.")
        
        # Import the original classifier
        try:
            from texture_classifier import run_classification_pipeline as original_pipeline
            return original_pipeline(
                input_dir=input_dir,
                confidence_threshold=confidence_threshold,
                device_pref=device_pref,
                output_list_path=output_list_path,
                output_results_path=output_results_path,
                is_file_list=is_file_list,
                valence_bias=valence_bias  # Pass valence bias to the original classifier too
            )
        except ImportError:
            print("Error: Could not import original texture classifier as fallback.")
            return False

# Simple test if run directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="VAD-based Texture Classification")
    parser.add_argument("--vad", required=True, help="Path to CSV file with VAD scores")
    parser.add_argument("--input", required=True, help="Directory with texture images or file list")
    parser.add_argument("--output_dir", default="results/vad_classification", help="Output directory")
    parser.add_argument("--confidence", type=float, default=0.6, help="Confidence threshold")
    parser.add_argument("--device", choices=["cuda", "cpu"], help="Device preference")
    parser.add_argument("--file_list", action="store_true", help="Input is a file list")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Define output paths
    output_list = os.path.join(args.output_dir, "high_confidence_list.txt")
    output_results = os.path.join(args.output_dir, "classification_results.txt")
    
    # Run the pipeline
    success = run_vad_classification_pipeline(
        vad_csv_path=args.vad,
        input_dir=args.input,
        confidence_threshold=args.confidence,
        device_pref=args.device,
        output_list_path=output_list,
        output_results_path=output_results,
        is_file_list=args.file_list
    )
    
    if success:
        print("VAD-based texture classification completed successfully.")
    else:
        print("VAD-based texture classification failed.")
        sys.exit(1) 