#!/usr/bin/env python
"""
This script converts texture images to depth maps using MiDaS model.
Refactored to be callable as a module.
"""

import os
import torch
import numpy as np
import cv2
from PIL import Image
import torchvision.transforms as transforms
from tqdm import tqdm
import sys
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
import torch.nn.functional as F # Import F for interpolate and pad
# import argparse # Removed argparse

# --- Core Logic Functions ---

def load_midas_model(model_type="DPT_Large", device_pref=None):
    """Load the specified MiDaS model and its transforms."""
    if device_pref:
        device = torch.device(device_pref)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"Loading MiDaS model ({model_type}) on {device}...")
    try:
        # Load MiDaS model from PyTorch Hub
        model = torch.hub.load("intel-isl/MiDaS", model_type) 
        model.to(device)
        model.eval()
        
        # Load appropriate transforms for the chosen model
        midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        if "DPT" in model_type:
            transform = midas_transforms.dpt_transform
            print("Using DPT transforms.")
        elif "MiDaS_small" in model_type:
             transform = midas_transforms.small_transform
             print("Using MiDaS small transforms.")
        else: # Default or other MiDaS models
             transform = midas_transforms.midas_transform
             print("Using standard MiDaS transforms.")

        print(f"Model ({model_type}) and transforms loaded successfully.")
        return model, transform, device
    except Exception as e:
        print(f"Error loading MiDaS model {model_type}: {e}")
        raise ImportError(f"Could not load MiDaS model {model_type}")

class DepthDataset(Dataset):
    """Custom Dataset for loading images for depth estimation."""
    def __init__(self, image_paths, transform):
        self.image_paths = image_paths
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        try:
            img = Image.open(image_path).convert('RGB')
            orig_width, orig_height = img.size
            img_np = np.array(img)
            # Apply transform (e.g., dpt_transform returns tensor)
            input_tensor = self.transform(img_np) 
            return input_tensor, (orig_width, orig_height), image_path
        except Exception as e:
            print(f"Error loading/processing image {image_path}: {e}")
            return None, (0, 0), image_path # Return None tensor to be filtered

def collate_fn(batch):
    """Collate function to handle None values and pad tensors."""
    # Filter out None entries
    batch = [item for item in batch if item[0] is not None]
    if not batch: return None, None, None 
    
    tensors, dims, paths = zip(*batch)
    
    # Find max H, W in the batch (tensors are typically [1, C, H, W] from MiDaS transforms)
    max_h = max(t.shape[2] for t in tensors) 
    max_w = max(t.shape[3] for t in tensors) 
    
    padded_tensors = []
    for t in tensors:
        h, w = t.shape[2], t.shape[3]
        pad_left = (max_w - w) // 2
        pad_right = max_w - w - pad_left
        pad_top = (max_h - h) // 2
        pad_bottom = max_h - h - pad_top
        padding = (pad_left, pad_right, pad_top, pad_bottom)
        padded_t = F.pad(t, padding, "constant", 0)
        padded_tensors.append(padded_t)
        
    # Stack along batch dimension and remove redundant dim 1
    try:
        # Stack creates [B, 1, C, max_h, max_w]
        tensor_batch = torch.stack(padded_tensors, dim=0) 
        # Squeeze to [B, C, max_h, max_w]
        tensor_batch = tensor_batch.squeeze(1) 
    except Exception as e:
         print(f"Error during tensor stacking/squeezing: {e}")
         # Debug shapes
         print("Shapes of padded tensors:", [t.shape for t in padded_tensors])
         return None, None, None # Indicate error

    return tensor_batch, list(dims), list(paths)

def generate_depth_map_batch(model, batch_input_tensors, device, batch_orig_dims):
    """Generate depth maps from a batch of preprocessed images."""
    processed_depth_maps = []
    with torch.no_grad():
        batch_input_tensors = batch_input_tensors.to(device)
        predictions = model(batch_input_tensors) # Model output shape depends on model type
        
        for i in range(predictions.shape[0]):
            prediction = predictions[i] 
            orig_width, orig_height = batch_orig_dims[i]

            # Ensure prediction is suitable for interpolation [1, 1, H, W] or [1, H, W]
            if len(prediction.shape) == 2: # If output is [H, W]
                 prediction = prediction.unsqueeze(0) # -> [1, H, W]
            if len(prediction.shape) == 3: # If output is [C, H, W] or [1, H, W]
                 prediction = prediction.unsqueeze(0) # -> [1, C, H, W] or [1, 1, H, W]

            # Resize prediction to original image size using interpolation
            interpolated_depth = F.interpolate(
                prediction,
                size=(orig_height, orig_width),
                mode="bicubic", 
                align_corners=False,
            ).squeeze() # Remove batch/channel dims -> [H, W]

            depth_np = interpolated_depth.cpu().numpy()
            
            # Normalize and enhance contrast (from original script)
            depth_min, depth_max = depth_np.min(), depth_np.max()
            epsilon = 1e-6
            if depth_max - depth_min < epsilon:
                normalized_depth = np.zeros_like(depth_np, dtype=np.uint8)
            else:
                normalized_depth = ((depth_np - depth_min) / (depth_max - depth_min + epsilon))
                gamma = 0.7 # Contrast enhancement
                normalized_depth = np.power(normalized_depth, gamma)
                normalized_depth = (normalized_depth * 255).astype(np.uint8)
                # Apply CLAHE for local contrast
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                normalized_depth = clahe.apply(normalized_depth)
            
            processed_depth_maps.append(normalized_depth)
            
    return processed_depth_maps

def save_depth_map(depth, output_path):
    """Save depth map as an image."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        success = cv2.imwrite(output_path, depth)
        if not success: print(f"Warning: cv2.imwrite failed for {output_path}")
    except Exception as e:
        print(f"Error saving depth map {output_path}: {e}")

def process_images(
    image_list_file, 
    output_dir, 
    model, 
    transform, 
    device, 
    batch_size=4, 
    num_workers=0
    ):
    """Process images listed in a file using batching."""
    
    image_files = []
    print(f"Reading image list from: {image_list_file}")
    try:
        with open(image_list_file, 'r') as f:
            image_files = [line.strip() for line in f if line.strip()] 
        if not image_files:
            print("Warning: Image list file is empty.")
            return False
        print(f"Found {len(image_files)} images in list file.")
    except Exception as e:
        print(f"Error reading image list file {image_list_file}: {e}")
        return False

    # Determine base input directory for relative path calculation (crucial for saving)
    # Assume paths in list are absolute or relative to a common (grand)parent dir.
    base_input_dir_for_relpath = None
    if image_files:
        try:
            # Find common parent directory of all listed files
            common_path = os.path.commonpath([os.path.abspath(p) for p in image_files])
            # Heuristic: Assume the 'images' folder is the relevant base if present
            if 'images' in common_path.split(os.sep):
                 base_input_dir_for_relpath = common_path.split('images')[0] + 'images'
            else: # Otherwise, use the direct common path
                 base_input_dir_for_relpath = common_path
            # If still not found, fallback to list file's directory
            if not base_input_dir_for_relpath:
                 base_input_dir_for_relpath = os.path.dirname(os.path.abspath(image_list_file))
        except Exception as e:
            print(f"Warning: Could not determine base path reliably: {e}. Using list file directory.")
            base_input_dir_for_relpath = os.path.dirname(os.path.abspath(image_list_file))
    else: # No images, cannot determine base path
         return False 

    print(f"Using base directory for relative output paths: {base_input_dir_for_relpath}")

    # --- Dataset, DataLoader, and Processing --- 
    dataset = DepthDataset(image_files, transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, collate_fn=collate_fn) 

    print(f"Starting batch processing with batch size {batch_size}...")
    processed_count = 0
    error_count = 0
    
    for batch_data in tqdm(dataloader, desc="Generating depth maps"):
        if batch_data is None or batch_data[0] is None:
            print("Skipping a batch due to loading errors.")
            error_count += batch_size # Approximate
            continue
            
        batch_input_tensors, batch_orig_dims, batch_image_paths = batch_data
        if not batch_image_paths: continue

        try:
            batch_depth_maps = generate_depth_map_batch(model, batch_input_tensors, device, batch_orig_dims)
            
            for i, depth_map in enumerate(batch_depth_maps):
                original_image_path = batch_image_paths[i]
                
                # Calculate relative path for saving, preserving structure
                try:
                     rel_path = os.path.relpath(original_image_path, start=base_input_dir_for_relpath)
                     # Handle cases where relpath might go up levels if base wasn't determined correctly
                     if rel_path.startswith(".."): 
                          rel_path = os.path.basename(original_image_path)
                          print(f"Warning: Relative path issue for {original_image_path}. Using filename only.")
                except ValueError: # Handles different drives on Windows
                    rel_path = os.path.basename(original_image_path)
                    print(f"Warning: Cross-drive path for {original_image_path}. Using filename only.")

                # Construct output path and change extension to .png
                output_path = os.path.join(output_dir, os.path.splitext(rel_path)[0] + ".png")
                
                save_depth_map(depth_map, output_path)
                processed_count += 1

        except Exception as e:
            print(f"\nError processing batch starting with image {batch_image_paths[0]}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            error_count += len(batch_image_paths)

    print(f"\nProcessed {processed_count} images.")
    if error_count > 0:
        print(f"Encountered errors during processing for approximately {error_count} images.")
        
    return processed_count > 0 # Return True if at least one image was processed

# --- Callable Pipeline Function ---

def run_depth_generation_pipeline(
    image_list_file, 
    output_dir, 
    model_type="DPT_Large", 
    batch_size=4, 
    num_workers=0, 
    device_pref=None
    ):
    """
    Runs the complete depth map generation pipeline.

    Args:
        image_list_file (str): Path to file containing list of image paths to process.
        output_dir (str): Directory to save the generated depth maps.
        model_type (str): Type of MiDaS model to use (e.g., "DPT_Large").
        batch_size (int): Batch size for processing.
        num_workers (int): Number of workers for DataLoader.
        device_pref (str or None): Preferred device ('cuda', 'cpu', or None for auto).

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # 1. Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Load Model
        model, transform, device = load_midas_model(model_type, device_pref) 
        
        # 3. Process images from the list file
        success = process_images(
            image_list_file=image_list_file,
            output_dir=output_dir, 
            model=model, 
            transform=transform, 
            device=device, 
            batch_size=batch_size, 
            num_workers=num_workers
        )
        
        if success:
            print("\nDepth map generation completed successfully!")
        else:
             print("\nDepth map generation finished, but some errors occurred or no images processed.")

        return success

    except Exception as e:
        print(f"An error occurred during the depth generation pipeline: {e}")
        import traceback
        print(traceback.format_exc())
        return False

# Removed the original main() function and if __name__ == "__main__": block
# The logic is now encapsulated in run_depth_generation_pipeline
