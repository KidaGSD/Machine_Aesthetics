import os
import cv2
import numpy as np
from tqdm import tqdm
import argparse
from skimage.feature import local_binary_pattern

def parse_args():
    parser = argparse.ArgumentParser(description='Convert color images to grayscale texture maps')
    parser.add_argument('--source', type=str, default='data/dtd/filtered_images',
                        help='Source directory containing DTD filtered images')
    parser.add_argument('--target', type=str, default='data/dtd/gray_textures',
                        help='Target directory for grayscale texture maps')
    parser.add_argument('--scale', type=float, default=1.0,
                        help='Resolution scaling factor (e.g., 2.0 for double resolution)')
    parser.add_argument('--detail', type=float, default=1.5,
                        help='Detail enhancement level (higher = more pronounced details)')
    parser.add_argument('--contrast', type=float, default=1.2,
                        help='Contrast enhancement level (higher = more contrast)')
    parser.add_argument('--fast', action='store_true',
                        help='Use faster processing (skip LBP for speed)')
    return parser.parse_args()

def extract_texture_details(image, detail_level=1.5, contrast_level=1.2, fast_mode=False):
    """
    Extract texture details from a color image and enhance them
    to create a grayscale texture map similar to a heightmap.
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        # Convert using luminance-preserving method
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Create multiple detail layers
    detail_layers = []
    weights = []
    
    # 1. Base grayscale layer with good contrast
    # Apply CLAHE for local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(gray)
    detail_layers.append(contrast_enhanced)
    weights.append(0.5 if fast_mode else 0.4)  # More weight in fast mode
    
    # 2. Edge detection layer to highlight texture boundaries
    # Use Sobel operator for edge detection
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    # Combine gradient magnitudes
    gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
    gradient_magnitude = cv2.normalize(gradient_magnitude, None, 0, 255, cv2.NORM_MINMAX)
    edge_layer = gradient_magnitude.astype(np.uint8)
    detail_layers.append(edge_layer)
    weights.append(0.3 if fast_mode else 0.25)  # More weight in fast mode
    
    # 3. Texture detail layer using Laplacian filter (fast)
    # This enhances fine texture details
    laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    laplacian = np.abs(laplacian)
    laplacian = cv2.normalize(laplacian, None, 0, 255, cv2.NORM_MINMAX)
    detail_layer = laplacian.astype(np.uint8)
    detail_layers.append(detail_layer)
    weights.append(0.2 if fast_mode else 0.25)  # Less weight in fast mode
    
    # 4. Local binary pattern for texture structure (optional, can be slow for large images)
    if not fast_mode:
        # Use scikit-image's optimized LBP implementation
        radius = 1
        n_points = 8
        lbp = local_binary_pattern(gray, n_points, radius, method='default')
        # Normalize to 0-255
        lbp = ((lbp - lbp.min()) / (lbp.max() - lbp.min() + 1e-10) * 255).astype(np.uint8)
        detail_layers.append(lbp)
        weights.append(0.1)
    
    # Blend all detail layers together with different weights
    result = np.zeros_like(gray, dtype=np.float32)
    
    # Apply weights and blend
    for i, layer in enumerate(detail_layers):
        # Add weighted layer
        result += weights[i] * layer.astype(np.float32)
    
    # Scale by detail level factor
    result = result * detail_level
    
    # Normalize to 0-255 range
    result = np.clip(result, 0, 255).astype(np.uint8)
    
    # Apply contrast enhancement
    if contrast_level != 1.0:
        # Create a contrast curve
        result_float = result.astype(np.float32) / 255.0
        result_contrast = (result_float - 0.5) * contrast_level + 0.5
        result = np.clip(result_contrast * 255, 0, 255).astype(np.uint8)
    
    # Final enhancement with CLAHE for better local contrast
    result = clahe.apply(result)
    
    return result

def process_image(input_path, output_path, scale_factor=1.0, detail_level=1.5, contrast_level=1.2, fast_mode=False):
    """Process a single image to create a grayscale texture map"""
    # Read the input image
    img = cv2.imread(input_path)
    
    if img is None:
        print(f"Error: Could not read {input_path}")
        return False
    
    # Resize if scaling is requested
    if scale_factor != 1.0:
        h, w = img.shape[:2]
        new_h, new_w = int(h * scale_factor), int(w * scale_factor)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    # Extract and enhance texture details
    texture_map = extract_texture_details(img, detail_level, contrast_level, fast_mode)
    
    # Save the result
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, texture_map)
    
    return True

def process_directory(source_dir, target_dir, scale_factor=1.0, detail_level=1.5, contrast_level=1.2, fast_mode=False):
    """Process all images in all subdirectories"""
    # Get all texture categories (subdirectories)
    categories = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]
    
    total_images = 0
    processed_images = 0
    
    # Process each category
    for category in categories:
        source_category_dir = os.path.join(source_dir, category)
        target_category_dir = os.path.join(target_dir, category)
        
        # Create target category directory
        os.makedirs(target_category_dir, exist_ok=True)
        
        # Get all image files in this category
        image_files = [f for f in os.listdir(source_category_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        print(f"Processing category: {category} ({len(image_files)} images)")
        
        # Process each image with progress bar
        for filename in tqdm(image_files, desc=category):
            total_images += 1
            
            source_path = os.path.join(source_category_dir, filename)
            target_path = os.path.join(target_category_dir, filename)
            
            # Process the image
            if process_image(source_path, target_path, scale_factor, detail_level, contrast_level, fast_mode):
                processed_images += 1
    
    return total_images, processed_images

def main():
    # Parse command line arguments
    args = parse_args()
    
    print(f"Converting color images to grayscale texture maps...")
    print(f"Source directory: {args.source}")
    print(f"Target directory: {args.target}")
    print(f"Settings: scale={args.scale}, detail={args.detail}, contrast={args.contrast}")
    print(f"Fast mode: {'ON' if args.fast else 'OFF'}")
    
    # Process all images
    total, processed = process_directory(
        args.source, 
        args.target, 
        args.scale, 
        args.detail, 
        args.contrast,
        args.fast
    )
    
    print(f"\nConversion complete!")
    print(f"Total images: {total}")
    print(f"Successfully processed: {processed}")
    print(f"Failed: {total - processed}")
    print(f"Grayscale texture maps saved to: {args.target}")

if __name__ == "__main__":
    main() 