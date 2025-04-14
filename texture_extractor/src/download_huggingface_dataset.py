import os
import sys
from pathlib import Path
from datasets import load_dataset
from PIL import Image
import tqdm

def download_textures_dataset(output_dir):
    """
    Download the dream-textures/textures-color-normal-1k dataset from Hugging Face
    and save it to the specified output directory.
    
    Args:
        output_dir: Path to the directory where the dataset should be saved
    """
    print(f"Downloading dream-textures/textures-color-normal-1k dataset to {output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create subdirectories for color and normal maps
    color_dir = os.path.join(output_dir, "color")
    normal_dir = os.path.join(output_dir, "normal")
    os.makedirs(color_dir, exist_ok=True)
    os.makedirs(normal_dir, exist_ok=True)
    
    # Download the dataset
    try:
        ds = load_dataset("dream-textures/textures-color-normal-1k")
        print(f"Dataset loaded successfully. Structure: {ds}")
        
        # Save the dataset to disk (metadata)
        ds.save_to_disk(output_dir)
        print(f"Dataset metadata saved to {output_dir}")
        
        # Extract and save actual image files
        print("\nExtracting images from dataset...")
        train_ds = ds["train"]
        
        for i, example in enumerate(tqdm.tqdm(train_ds, desc="Saving images")):
            # Get color and normal images
            color_img = example["color"]
            normal_img = example["normal"]
            
            # Save images to disk with index as filename
            color_path = os.path.join(color_dir, f"texture_{i:04d}_color.png")
            normal_path = os.path.join(normal_dir, f"texture_{i:04d}_normal.png")
            
            color_img.save(color_path)
            normal_img.save(normal_path)
        
        # Print dataset statistics
        print("\nDataset Statistics:")
        for split in ds:
            print(f"Split: {split}, Size: {len(ds[split])}")
        
        print(f"\nColor images saved to: {color_dir}")
        print(f"Normal maps saved to: {normal_dir}")
        
        return True
    except Exception as e:
        print(f"Error processing dataset: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Get the repository root directory (assuming this script is in src/)
    src_dir = Path(__file__).parent
    repo_root = src_dir.parent
    
    # Default output directory is "data/hugging_data" relative to repo root
    default_output_dir = repo_root / "data" / "hugging_data"
    
    # Allow custom output directory via command line argument
    output_dir = sys.argv[1] if len(sys.argv) > 1 else default_output_dir
    
    # Download the dataset
    success = download_textures_dataset(output_dir)
    
    if success:
        print("\nDataset download and extraction completed successfully.")
    else:
        print("\nDataset download or extraction failed.")
        sys.exit(1) 