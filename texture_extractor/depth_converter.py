#!/usr/bin/env python
"""
This script converts texture images to depth maps using MiDaS model and integrates with CLIP classification.
"""

import os
import torch
import numpy as np
import cv2
from PIL import Image
import torchvision.transforms as transforms
from tqdm import tqdm
import argparse
import sys
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
import torch.nn.functional as F # Import F for interpolate and pad

def load_midas_model(device=None):
    """Load the MiDaS model and its transforms."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load MiDaS model
    print("Loading MiDaS DPT model (higher quality version)...")
    # Use DPT-Large for higher quality depth maps
    model = torch.hub.load("intel-isl/MiDaS", "DPT_Large") 
    model.to(device)
    model.eval()
    
    # Load appropriate transforms for the chosen model
    print("Loading MiDaS transforms for DPT model...")
    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    # Use dpt_transform for DPT model
    transform = midas_transforms.dpt_transform 
    
    print(f"Model (DPT_Large) and transforms loaded on {device}")
    return model, transform, device

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
            # Open and convert image to RGB
            img = Image.open(image_path).convert('RGB')
            
            # Store original dimensions
            orig_width, orig_height = img.size

            # Convert to NumPy array if needed by the transform (MiDaS transforms usually need this)
            img_np = np.array(img)
            
            # Apply transform
            # Note: MiDaS dpt_transform returns tensors directly, often [1, C, H, W]
            input_tensor = self.transform(img_np) 
            
            # Removed the shape check here, assuming transform is consistent

            return input_tensor, (orig_width, orig_height), image_path
        except Exception as e:
            print(f"Error loading or processing image {image_path}: {e}")
            # Return None or placeholder to be filtered later in collate_fn if needed
            return None, (0, 0), image_path 

# Optional: Collate function to handle potential None values from dataset errors
def collate_fn(batch):
    # Filter out None entries where the tensor couldn't be loaded/processed
    batch = [item for item in batch if item[0] is not None]
    if not batch:
        return None, None, None # Return None if the whole batch failed
    
    # Unzip the batch
    tensors, dims, paths = zip(*batch) # tensors is a tuple of [1, C, H, W] tensors
    
    # Find the maximum height and width in the batch
    # Tensors are ACTUALLY [1, C, H, W] from the transform
    max_h = max(t.shape[2] for t in tensors) # Index 2 for Height
    max_w = max(t.shape[3] for t in tensors) # Index 3 for Width
    
    # Pad each tensor to the max size
    padded_tensors = []
    for t in tensors: # t is [1, C, H, W]
        h, w = t.shape[2], t.shape[3]
        # Calculate padding: (left, right, top, bottom) for the H, W dimensions
        pad_left = (max_w - w) // 2
        pad_right = max_w - w - pad_left
        pad_top = (max_h - h) // 2
        pad_bottom = max_h - h - pad_top
        
        padding = (pad_left, pad_right, pad_top, pad_bottom)
        
        # Pad the tensor (1, C, H, W). Padding applies to the last two dimensions (H, W).
        padded_t = F.pad(t, padding, "constant", 0) # Pad with 0
        # padded_t should now be [1, C, max_h, max_w]
        padded_tensors.append(padded_t)
        
    # Stack the padded tensors along the batch dimension.
    # Input tensors are [1, C, max_h, max_w], stacking creates [B, 1, C, max_h, max_w]
    tensor_batch = torch.stack(padded_tensors, dim=0)
    
    # Squeeze the redundant dimension 1 introduced by the transform/stacking
    tensor_batch = tensor_batch.squeeze(1) # Resulting shape: [B, C, max_h, max_w]
    
    return tensor_batch, list(dims), list(paths)


# Removed preprocess_image function as logic moved to DepthDataset

def generate_depth_map(model, batch_input_tensors, device, batch_orig_dims):
    """Generate depth maps from a batch of preprocessed images."""
    processed_depth_maps = []
    with torch.no_grad():
        # Move the entire batch to the device
        batch_input_tensors = batch_input_tensors.to(device)
        
        # Get predictions for the whole batch
        predictions = model(batch_input_tensors)
        
        # Process each prediction in the batch
        for i in range(predictions.shape[0]):
            prediction = predictions[i] # Shape [H_pred, W_pred] or [1, H_pred, W_pred] ? Check model output
            orig_width, orig_height = batch_orig_dims[i]

            # Add channel dim if model outputs [H, W] -> [1, H, W] for interpolate
            if len(prediction.shape) == 2:
                 prediction = prediction.unsqueeze(0) 
            
            # Add batch dim -> [1, 1, H, W] for interpolate
            prediction = prediction.unsqueeze(0) 

            # Resize prediction to original image size
            # Interpolation can run on GPU
            interpolated_depth = F.interpolate(
                prediction,
                size=(orig_height, orig_width),
                mode="bicubic", # Use bicubic for better quality
                align_corners=False,
            ).squeeze() # Squeeze removes batch and channel -> [H, W]

            # Convert to numpy array (needs CPU tensor)
            depth_np = interpolated_depth.cpu().numpy()
            
            # Enhanced normalization to preserve more texture details
            depth_min = depth_np.min()
            depth_max = depth_np.max()
            epsilon = 1e-6
            
            if depth_max - depth_min < epsilon:
                normalized_depth = np.zeros_like(depth_np, dtype=np.uint8)
            else:
                # Apply improved normalization with increased contrast
                normalized_depth = ((depth_np - depth_min) / (depth_max - depth_min + epsilon))
                
                # Apply contrast enhancement using gamma correction
                gamma = 0.7  # Values < 1 increase contrast in darker regions
                normalized_depth = np.power(normalized_depth, gamma)
                
                # Apply histogram equalization for better texture visibility
                # Convert to 8-bit for histogram equalization
                normalized_depth = (normalized_depth * 255).astype(np.uint8)
                
                # Apply adaptive histogram equalization for better local contrast
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                normalized_depth = clahe.apply(normalized_depth)
            
            processed_depth_maps.append(normalized_depth)
            
    return processed_depth_maps

def save_depth_map(depth, output_path):
    """Save depth map as an image."""
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        success = cv2.imwrite(output_path, depth)
        if not success:
            print(f"Warning: cv2.imwrite failed for {output_path}")
    except Exception as e:
        print(f"Error saving depth map {output_path}: {e}")


def process_directory(
    input_dir, 
    output_dir, 
    model, 
    transform, 
    device, 
    batch_size=4, 
    num_workers=0, 
    max_images_per_category=None, # Changed default to None
    image_list_file=None # New argument
    ):
    """Process images using batching. Reads from image_list_file if provided, otherwise scans input_dir."""
    
    image_files = []
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']

    # --- Determine input images --- 
    if image_list_file:
        print(f"Reading image list from: {image_list_file}")
        try:
            with open(image_list_file, 'r') as f:
                # Read paths, strip whitespace/newlines
                image_files = [line.strip() for line in f if line.strip()] 
            print(f"Found {len(image_files)} images in list file.")
            if not image_files:
                print("Warning: Image list file is empty.")
                return
        except FileNotFoundError:
            print(f"Error: Image list file not found: {image_list_file}")
            return
        except Exception as e:
            print(f"Error reading image list file {image_list_file}: {e}")
            return
    elif input_dir:
        print(f"Scanning input directory: {input_dir}")
        if max_images_per_category is not None and max_images_per_category > 0:
            # Scan limited images per category
            print(f"Limiting to {max_images_per_category} images per category.")
            # Iterate through subdirectories (categories)
            for category_dir in Path(input_dir).iterdir():
                if category_dir.is_dir():
                    category_name = category_dir.name
                    # print(f"  Scanning category: {category_name}") # Less verbose
                    category_images = []
                    count = 0
                    for entry in os.scandir(category_dir):
                        if entry.is_file() and any(entry.name.lower().endswith(ext) for ext in image_extensions):
                            if count < max_images_per_category:
                                category_images.append(entry.path)
                                count += 1
                            else:
                                break # Stop once max images for this category are found
                    image_files.extend(category_images)
        else:
            # Scan all images in the directory and subdirectories
            print("Scanning for all images in directory...")
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        # Use absolute path for consistency
                        image_files.append(os.path.abspath(os.path.join(root, file))) 
    else:
        print("Error: Must provide either --input_dir or --image_list_file.")
        return

    # --- Check if any images were found --- 
    if not image_files:
        print(f"No images found to process.")
        return
    
    print(f"\nTotal images to process: {len(image_files)}")

    # --- Proceed with Dataset, DataLoader, and processing --- 
    dataset = DepthDataset(image_files, transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, collate_fn=collate_fn) 

    print(f"Starting batch processing with batch size {batch_size}...")
    processed_count = 0
    error_count = 0
    # Store the base input directory path for relative path calculation
    base_input_dir_for_relpath = None
    if image_list_file:
        if image_files: # Make sure list is not empty
            try:
                # Get the directory of the first file
                first_file_dir = os.path.dirname(image_files[0])
                # Go up two levels to get the assumed base (e.g., from .../images/category/ -> .../images/)
                # This assumes the structure from the classifier list file is consistent
                base_input_dir_for_relpath = os.path.abspath(os.path.join(first_file_dir, "..", "..")) 
            except Exception as e:
                print(f"Warning: Could not automatically determine base path from image list file: {e}")
        if not base_input_dir_for_relpath: # Fallback if determination failed
             print("Warning: Falling back to using the directory of the list file for relative paths.")
             base_input_dir_for_relpath = os.path.dirname(os.path.abspath(image_list_file))
    else:
        # If using input_dir, that's our base
        base_input_dir_for_relpath = input_dir

    # Final check and fallback
    if not base_input_dir_for_relpath:
         print("Error: Could not determine base input directory for relative path calculation.")
         # As a last resort, maybe just don't use relative paths?
         # For now, stick to the previous fallback:
         base_input_dir_for_relpath = "." 
         print(f"Warning: Using current directory '{base_input_dir_for_relpath}' as base for relative paths.")

    print(f"Using base directory for relative output paths: {base_input_dir_for_relpath}")

    for batch_data in tqdm(dataloader, desc="Generating depth maps"):
        if batch_data is None: # Check if collate_fn returned None
            print("Skipping a batch due to loading errors.")
            error_count += batch_size # Approximate error count
            continue
            
        batch_input_tensors, batch_orig_dims, batch_image_paths = batch_data
        
        if batch_input_tensors is None: # Double check after unpacking
            print("Skipping a batch due to loading errors.")
            error_count += len(batch_image_paths) if batch_image_paths else batch_size
            continue

        if not batch_image_paths:
             continue

        try:
            batch_depth_maps = generate_depth_map(model, batch_input_tensors, device, batch_orig_dims)
            
            for i, depth_map in enumerate(batch_depth_maps):
                original_image_path = batch_image_paths[i]
                
                # Try to make the output path relative to the *original* base input dir
                try:
                     rel_path = os.path.relpath(original_image_path, start=base_input_dir_for_relpath)
                     # We no longer need the check for ".." here because relpath should now 
                     # correctly produce paths like "category/image.jpg" relative to the common base.
                     # if rel_path.startswith(".."):
                     #     rel_path = os.path.basename(original_image_path)

                except ValueError: # Happens on Windows if paths are on different drives
                    rel_path = os.path.basename(original_image_path)
                    print(f"Warning: Could not determine relative path for {original_image_path}. Using filename only.")

                output_path = os.path.join(output_dir, rel_path)
                output_path = os.path.splitext(output_path)[0] + ".png"
                
                save_depth_map(depth_map, output_path)
                processed_count += 1

        except Exception as e:
            print(f"Error processing batch starting with image {batch_image_paths[0]}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            error_count += len(batch_image_paths)

    print(f"Processed {processed_count} images.")
    if error_count > 0:
        print(f"Encountered errors during processing for approximately {error_count} images.")

def main():
    """Main function."""
    # Get script directory for relative paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Convert texture images to depth maps using batch processing.")
    # Input can be directory OR list file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input_dir", help="Directory containing input images (scanned if image_list_file not provided)")
    group.add_argument("--image_list_file", help="File containing a list of image paths to process (one per line).")
    
    parser.add_argument("--output_dir", required=True, help="Directory to save depth maps")
    parser.add_argument("--batch_size", type=int, default=4, help="Batch size for processing (default: 4)") 
    parser.add_argument("--num_workers", type=int, default=0, help="Number of workers for DataLoader (0 recommended on Windows)")
    parser.add_argument("--device", choices=["cuda", "cpu"], default=None, help="Device to use (default: auto-detect)")
    parser.add_argument("--max_images_per_category", type=int, default=None, help="Maximum images to process per category subdirectory (only used if --input_dir is provided and --image_list_file is not)")
    
    args = parser.parse_args()
    
    # Resolve paths relative to script directory
    if args.input_dir and not os.path.isabs(args.input_dir):
        input_dir = os.path.join(script_dir, args.input_dir)
    else:
        input_dir = args.input_dir
        
    if args.image_list_file and not os.path.isabs(args.image_list_file):
        image_list_file = os.path.join(script_dir, args.image_list_file)
    else:
        image_list_file = args.image_list_file
        
    if not os.path.isabs(args.output_dir):
        output_dir = os.path.join(script_dir, args.output_dir)
    else:
        output_dir = args.output_dir
    
    # Check if input exists
    if input_dir and not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' doesn't exist")
        return
        
    if image_list_file and not os.path.exists(image_list_file):
        print(f"Error: Image list file '{image_list_file}' doesn't exist")
        return
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Set device
    if args.device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    
    print(f"Using device: {device}")
    
    # Load model and transforms (defaults to small)
    model, transform, _ = load_midas_model(device) 
    
    # Process based on provided input (dir or list file)
    process_directory(
        input_dir, # Can be None if list file is used
        output_dir, 
        model, 
        transform, 
        device, 
        args.batch_size, 
        args.num_workers,
        args.max_images_per_category,
        image_list_file # Pass the list file arg
    )
    
    print("\nDepth map generation completed!")

if __name__ == "__main__":
    main() 