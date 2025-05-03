import os
import cv2
import numpy as np
from tqdm import tqdm

# Set paths
source_dir = 'data/hugging_data/normal_clean'
target_dir = 'data/hugging_data/normal_grey'

# Create target directory if it doesn't exist
os.makedirs(target_dir, exist_ok=True)

def convert_normal_to_grayscale(input_path, output_path, light_angle='omnidirectional', scale_factor=1.0,
                               quality=100, detail_level=1.2):
    """
    Convert a normal map to grayscale using all three channels (RGB) for
    proper height and directional information.
    
    Parameters:
    - input_path: Path to the input normal map
    - output_path: Path to save the output grayscale image
    - light_angle: Direction of simulated light or 'omnidirectional' for all directions
    - scale_factor: Factor to scale the output resolution (e.g., 2.0 = double resolution)
    - quality: JPEG quality (1-100) if saving as JPEG
    - detail_level: Strength of detail enhancement (higher = more pronounced)
    """
    # Read the normal map image at full resolution
    normal_map = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    
    if normal_map is None:
        print(f"Error: Could not read {input_path}")
        return False
    
    # Upscale the image if requested (before channel processing for better detail)
    original_h, original_w = normal_map.shape[:2]
    
    if scale_factor != 1.0:
        new_w = int(original_w * scale_factor)
        new_h = int(original_h * scale_factor)
        # Use INTER_CUBIC for upscaling (better quality than INTER_LINEAR)
        normal_map = cv2.resize(normal_map, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    
    # Split the channels (OpenCV uses BGR order)
    b_channel, g_channel, r_channel = cv2.split(normal_map)
    
    # Convert to float32 for processing
    b_float = b_channel.astype(np.float32)
    g_float = g_channel.astype(np.float32)
    r_float = r_channel.astype(np.float32)
    
    # In normal maps: R=X, G=Y, B=Z (with values typically centered at 128)
    # Center each channel at 0 for proper directional calculation
    r_centered = r_float - 128.0  # X-axis (left/right)
    g_centered = g_float - 128.0  # Y-axis (up/down)
    b_centered = b_float - 128.0  # Z-axis (depth/height)
    
    # Create the base height map from Z-axis (blue channel)
    # Use moderate scaling to maintain good midtones
    height_map = b_centered * 0.8
    
    # Create a base heightmap centered at middle gray (neutral point)
    base_image = np.clip(height_map + 128.0, 0, 255).astype(np.uint8)
    
    if light_angle == 'omnidirectional':
        # Omnidirectional lighting approach - combine information from all directions
        
        # Calculate gradient magnitude from X and Y components
        # This gives us the "slope steepness" at each pixel
        gradient_magnitude = np.sqrt(r_centered**2 + g_centered**2) * detail_level * 0.7
        
        # Create directional lighting from 4 main directions
        lighting_directions = []
        
        # Top-left lighting
        top_left = (-r_centered + g_centered) * 0.4
        lighting_directions.append(top_left)
        
        # Top-right lighting
        top_right = (r_centered + g_centered) * 0.4
        lighting_directions.append(top_right)
        
        # Bottom-left lighting
        bottom_left = (-r_centered - g_centered) * 0.4
        lighting_directions.append(bottom_left)
        
        # Bottom-right lighting
        bottom_right = (r_centered - g_centered) * 0.4
        lighting_directions.append(bottom_right)
        
        # Combine all lighting directions to create an "ambient occlusion" effect
        # This gives depth to all features regardless of orientation
        ambient_occlusion = np.zeros_like(r_centered)
        for direction in lighting_directions:
            # Normalize and add each direction's contribution
            contribution = np.clip(direction + 128.0, 0, 255) / 255.0
            ambient_occlusion += contribution
        
        # Normalize and scale ambient occlusion
        ambient_occlusion = ambient_occlusion / len(lighting_directions)
        ambient_occlusion = np.clip(ambient_occlusion * 255.0, 0, 255).astype(np.uint8)
        
        # Apply gradient magnitude as edge details
        # Higher gradient = steeper slope = more pronounced edge
        edge_details = np.clip(gradient_magnitude + 128.0, 0, 255).astype(np.uint8)
        
        # Blend base height, ambient occlusion, and edge details
        blended = np.zeros_like(base_image)
        
        # Multi-step blending process for rich detail:
        # 1. Start with base height
        # 2. Apply ambient occlusion with soft light blend
        # 3. Enhance edges with overlay blend
        
        # Helper functions for blending
        def soft_light_blend(base, blend):
            """Photoshop-style soft light blend mode"""
            base_norm = base.astype(np.float32) / 255.0
            blend_norm = blend.astype(np.float32) / 255.0
            
            result = np.where(
                blend_norm < 0.5,
                base_norm - (1.0 - 2.0 * blend_norm) * base_norm * (1.0 - base_norm),
                base_norm + (2.0 * blend_norm - 1.0) * (np.sqrt(base_norm) - base_norm)
            )
            
            return np.clip(result * 255.0, 0, 255).astype(np.uint8)
        
        def overlay_blend(base, blend):
            """Photoshop-style overlay blend mode"""
            base_norm = base.astype(np.float32) / 255.0
            blend_norm = blend.astype(np.float32) / 255.0
            
            result = np.where(
                base_norm < 0.5,
                2.0 * base_norm * blend_norm,
                1.0 - 2.0 * (1.0 - base_norm) * (1.0 - blend_norm)
            )
            
            return np.clip(result * 255.0, 0, 255).astype(np.uint8)
        
        # Apply ambient occlusion with soft light blend
        blended = soft_light_blend(base_image, ambient_occlusion)
        
        # Apply edge details with overlay blend (slightly reduced opacity)
        edge_overlay = cv2.addWeighted(blended, 0.7, edge_details, 0.3, 0)
        blended = overlay_blend(blended, edge_overlay)
        
    else:
        # Single directional lighting (original approach)
        # Adjust direction based on light_angle
        if 'left' in light_angle:
            r_centered = -r_centered  # Invert X for light from left
        
        if 'bottom' in light_angle:
            g_centered = -g_centered  # Invert Y for light from bottom
        
        # Combine R and G channels for directional lighting
        # Weight them according to the lighting angle
        x_weight = 0.6
        y_weight = 0.6
        
        # Create a directional lighting layer
        directional = r_centered * x_weight + g_centered * y_weight
        
        # Scale and shift the directional lighting to 0-255 range
        directional_image = np.clip(directional + 128.0, 0, 255).astype(np.uint8)
        
        # Blend the height information with directional lighting
        # Using a custom blend mode that preserves both height and directional details
        def blend_normal_components(height, directional):
            """Blend height and directional components with proper balance"""
            # Normalize to 0-1 range
            h = height.astype(np.float32) / 255.0
            d = directional.astype(np.float32) / 255.0
            
            # Apply a modified soft light blend (gives good results for normal maps)
            # This formula enhances contrast while preserving midtones
            result = np.where(
                d < 0.5,
                h * (d + 0.5),  # Darker directional darkens height
                h + (2 * d - 1) * (np.sqrt(h) - h)  # Lighter directional lightens height
            )
            
            # Ensure we stay in 0-1 range
            return np.clip(result * 255.0, 0, 255).astype(np.uint8)
        
        # Blend the components
        blended = blend_normal_components(base_image, directional_image)
    
    # Apply local contrast enhancement to bring out fine details
    # Use a reasonable clipLimit to avoid over-brightening
    # Adjust tile size based on resolution
    tile_size = max(8, min(16, int(blended.shape[0] / 64)))
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(tile_size, tile_size))
    enhanced = clahe.apply(blended)
    
    # Add moderate sharpening for details
    # Adjust sigma based on resolution
    sigma = 2.0 * scale_factor
    blur = cv2.GaussianBlur(enhanced, (0, 0), sigma)
    sharp = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
    
    # Fine-tune the overall brightness and contrast
    # Ensure we have a good balance of shadows, midtones and highlights
    final = cv2.convertScaleAbs(sharp, alpha=1.0, beta=-10)  # Slight darkening
    
    # Determine output format and quality settings
    _, ext = os.path.splitext(output_path)
    if ext.lower() == '.jpg' or ext.lower() == '.jpeg':
        # Save as JPEG with specified quality
        cv2.imwrite(output_path, final, [cv2.IMWRITE_JPEG_QUALITY, quality])
    else:
        # For other formats like PNG, use lossless compression
        cv2.imwrite(output_path, final, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    
    # Print resolution info if upscaled
    if scale_factor != 1.0:
        print(f"Upscaled: {os.path.basename(output_path)} from {original_w}x{original_h} to {new_w}x{new_h}")
    
    return True

# Function to parse arguments from command line
def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description='Convert normal maps to grayscale')
    parser.add_argument('--scale', type=float, default=1.0, 
                        help='Scale factor for resolution (e.g., 2.0 for double resolution)')
    parser.add_argument('--quality', type=int, default=95,
                        help='JPEG quality (1-100) if saving as JPEG')
    parser.add_argument('--light', type=str, default='omnidirectional',
                        choices=['omnidirectional', 'top-left', 'top-right', 'bottom-left', 'bottom-right'],
                        help='Light direction')
    parser.add_argument('--detail', type=float, default=1.2,
                        help='Detail enhancement level (1.0 = normal, higher = more detail)')
    return parser.parse_args()

# Main processing
if __name__ == "__main__":
    # Parse arguments
    args = parse_args()
    
    print(f"Converting normal maps to grayscale...")
    print(f"Settings: scale={args.scale}, light={args.light}, detail={args.detail}")
    
    successful = 0
    failed = 0

    # List all files and use tqdm for progress bar
    files = [f for f in os.listdir(source_dir) if f.endswith('.png')]

    for filename in tqdm(files):
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        
        # Convert the normal map with specified options
        if convert_normal_to_grayscale(
            source_path, 
            target_path, 
            light_angle=args.light,
            scale_factor=args.scale,
            quality=args.quality,
            detail_level=args.detail
        ):
            successful += 1
        else:
            failed += 1

    print(f"Conversion complete!")
    print(f"Successfully converted: {successful}")
    print(f"Failed: {failed}")
    print(f"Grayscale normal maps saved to: {target_dir}")
    print(f"Light angle: {args.light}")
    if args.light == 'omnidirectional':
        print("- Using omnidirectional lighting to capture all elevation details") 