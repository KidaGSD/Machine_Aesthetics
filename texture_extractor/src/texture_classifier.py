import os
import torch
import sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms
# from sklearn.metrics import confusion_matrix # Keep if needed for internal eval, remove if not
# import seaborn as sns # Keep if needed for internal eval, remove if not
from tqdm import tqdm
import importlib
import subprocess
# import argparse # Removed argparse

# Define the emotions we want to classify (Keep this accessible)
emotions = [
    "joyful", "peaceful", "serene", "anxious", "angry", 
    "sad", "fearful", "disgusted", "surprised", "excited"
]

# DTD-specific categories mapping (Keep this accessible if used)
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

# --- Core Logic Functions (extracted from original main/helpers) ---

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

def prepare_text_features(model, text_labels, device):
    """Encode the text prompts."""
    clip = import_clip()
    if clip is None:
        raise ImportError("CLIP module not available for tokenization.")
        
    # Use a standard prompt template
    text_inputs = torch.cat([clip.tokenize(f"A texture that feels {label}") for label in text_labels]).to(device)
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

def classify_images(model, preprocess, text_features, image_paths, device, text_labels):
    """Classify images using CLIP and return detailed results."""
    results = []
    model.eval() # Ensure model is in eval mode

    # Determine batch size (optional, could be a parameter)
    batch_size = 32 # Example batch size, adjust based on GPU memory
    
    print(f"Classifying {len(image_paths)} images (batch size: {batch_size})...")
    
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
            continue # Skip if batch is empty after errors

        # Stack images into a batch tensor
        image_input = torch.stack(batch_images).to(device)
        
        # Perform inference
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
            # Calculate similarity
            # image_features: [batch_size, embedding_dim]
            # text_features: [num_labels, embedding_dim]
            # similarity: [batch_size, num_labels]
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
        # Process results for each image in the batch
        similarity_cpu = similarity.cpu().numpy()
        for j, image_path in enumerate(valid_paths_in_batch):
            scores = similarity_cpu[j]
            # Get all scores, sorted by confidence
            sorted_indices = np.argsort(scores)[::-1]
            top_emotions = [(text_labels[idx], scores[idx]) for idx in sorted_indices]
            
            results.append({
                "image_path": image_path,
                "top_emotions": top_emotions # Store all scores, sorted
            })
            
    return results

def save_results(results, confidence_threshold, output_list_path, output_results_path):
    """Filter results by confidence and save the list and detailed scores."""
    high_confidence_paths = []
    
    print(f"Filtering results with confidence threshold >= {confidence_threshold}")
    
    # Ensure output directories exist
    os.makedirs(os.path.dirname(output_list_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_results_path), exist_ok=True)

    try:
        with open(output_results_path, "w", encoding='utf-8') as f_details:
            for result in results:
                f_details.write(f"Image: {result['image_path']}\n")
                top_conf = -1
                passed_threshold = False
                if result["top_emotions"]:
                    top_emotion, top_conf = result["top_emotions"][0]
                    if top_conf >= confidence_threshold:
                        passed_threshold = True
                        high_confidence_paths.append(result['image_path'])
                    
                    for i, (emotion, score) in enumerate(result["top_emotions"]):
                        f_details.write(f"- {emotion}: {score:.4f}\n")
                        # Add DTD categories mapping if relevant (optional)
                        # if emotion in dtd_categories:
                        #     f_details.write(f"  Related DTD categories: {', '.join(dtd_categories[emotion])}\n")
                
                f_details.write(f"Passed Threshold ({confidence_threshold}): {'YES' if passed_threshold else 'NO'}\n\n")
        print(f"Saved detailed classification results to: {output_results_path}")

    except Exception as e:
        print(f"Error writing detailed results to {output_results_path}: {e}")
        return False # Indicate failure

    try:
        with open(output_list_path, "w", encoding='utf-8') as f_list:
            for img_path in high_confidence_paths:
                f_list.write(f"{img_path}\n")
        print(f"Saved list of {len(high_confidence_paths)} high-confidence image paths to: {output_list_path}")
    except Exception as e:
        print(f"Error writing high-confidence list to {output_list_path}: {e}")
        return False # Indicate failure
        
    return True # Indicate success

# --- Callable Pipeline Function ---

def run_classification_pipeline(input_dir, confidence_threshold, device_pref, output_list_path, output_results_path, is_file_list=False):
    """
    Runs the complete classification pipeline.

    Args:
        input_dir (str): Directory containing input texture images or a text file with image paths.
        confidence_threshold (float): Minimum confidence score for the top emotion.
        device_pref (str or None): Preferred device ('cuda', 'cpu', or None for auto).
        output_list_path (str): Path to save the list of high-confidence images.
        output_results_path (str): Path to save the detailed classification scores.
        is_file_list (bool): If True, input_dir is a text file with image paths.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # 1. Load Model
        model, preprocess, device = load_clip_model(device_pref)
        
        # 2. Prepare Text Features (using the global 'emotions' list)
        text_features = prepare_text_features(model, emotions, device)
        
        # 3. Find Images
        if is_file_list:
            # Read image paths from the provided file
            try:
                with open(input_dir, 'r') as f:
                    image_paths = [line.strip() for line in f if line.strip()]
                print(f"Read {len(image_paths)} image paths from file: {input_dir}")
            except Exception as e:
                print(f"Error reading image paths from file {input_dir}: {e}")
                return False
        else:
            # Scan directory for images
            image_paths = find_images(input_dir)
            
        if not image_paths:
            print("No images found. Exiting.")
            return False
            
        # 4. Classify Images
        results = classify_images(model, preprocess, text_features, image_paths, device, emotions)
        
        # 5. Filter and Save Results
        success = save_results(results, confidence_threshold, output_list_path, output_results_path)
        
        # 6. Optional: Internal visualizations (can be disabled or moved)
        # visualize_results(results, emotions, input_dir) # This was in the old main, might move to evaluation module
        
        return success

    except Exception as e:
        print(f"An error occurred during the classification pipeline: {e}")
        import traceback
        print(traceback.format_exc())
        return False

# Removed the original main() function and if __name__ == "__main__": block
# The logic is now encapsulated in run_classification_pipeline
