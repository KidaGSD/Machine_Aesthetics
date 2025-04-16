import os
import glob
import json

def detect_dataset_type(texture_path):
    """
    Detect whether a texture path is from the DTD dataset or Hugging Face dataset.
    
    Args:
        texture_path: Path to a texture file
    
    Returns:
        str: 'dtd' or 'huggingface'
    """
    if 'hugging_data' in texture_path:
        return 'huggingface'
    elif 'dtd' in texture_path:
        return 'dtd'
    else:
        # Default to dtd for backward compatibility
        return 'dtd'

def get_normal_map_path(texture_path):
    """
    Get the corresponding normal map path for a texture.
    For huggingface dataset, transforms color path to normal path.
    For dtd dataset, transforms to depth maps directory.
    
    Args:
        texture_path: Path to a texture file
    
    Returns:
        str: Path to the corresponding normal/depth map
    """
    dataset_type = detect_dataset_type(texture_path)
    
    if dataset_type == 'huggingface':
        # For huggingface dataset, replace 'color' with 'normal' in the path
        # Example: data/hugging_data/color/texture_0001_color.png -> data/hugging_data/normal/texture_0001_normal.png
        normal_path = texture_path.replace('color', 'normal').replace('_color.png', '_normal.png')
        if os.path.exists(normal_path):
            return normal_path
        else:
            print(f"Warning: Normal map not found at {normal_path}")
            return None
    else:
        # For DTD dataset, use the generated depth maps from depth_maps directory
        # Example: data/dtd/images/banded/banded_0001.jpg -> results/depth_maps/banded/banded_0001.jpg.png
        base_name = os.path.basename(texture_path)
        depth_dir = texture_path.replace('dtd/images', 'results/depth_maps')
        depth_path = os.path.join(os.path.dirname(depth_dir), f"{base_name}.png")
        if os.path.exists(depth_path):
            return depth_path
        else:
            print(f"Warning: Depth map not found at {depth_path}")
            return None

def is_normal_map_available(texture_path):
    """
    Check if a normal/depth map is available for the given texture path.
    
    Args:
        texture_path: Path to a texture file
    
    Returns:
        bool: True if the normal/depth map exists, False otherwise
    """
    normal_path = get_normal_map_path(texture_path)
    return normal_path is not None and os.path.exists(normal_path)

def find_textures_by_dataset(base_dir, dataset_type=None):
    """
    Find all texture files in the specified dataset type.
    
    Args:
        base_dir: Base directory to search in
        dataset_type: 'dtd', 'huggingface', or None (for both)
    
    Returns:
        list: List of texture file paths
    """
    textures = []
    
    if dataset_type in [None, 'dtd']:
        # Find DTD textures
        dtd_dir = os.path.join(base_dir, 'data', 'dtd', 'images')
        if os.path.exists(dtd_dir):
            for texture_path in glob.glob(os.path.join(dtd_dir, '*', '*.jpg')):
                textures.append(texture_path)
    
    if dataset_type in [None, 'huggingface']:
        # Find Hugging Face textures
        hf_dir = os.path.join(base_dir, 'data', 'hugging_data', 'color')
        if os.path.exists(hf_dir):
            for texture_path in glob.glob(os.path.join(hf_dir, '*.png')):
                textures.append(texture_path)
    
    return textures
