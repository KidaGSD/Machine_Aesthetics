#!/usr/bin/env python
"""
This script downloads and sets up the Describable Textures Dataset (DTD) for use with the texture emotion classifier.
"""

import os
import subprocess
import shutil
from pathlib import Path

def download_dtd():
    """Download the DTD dataset using Kaggle API."""
    print("Downloading DTD dataset...")
    try:
        # Create a directory for the dataset if it doesn't exist
        dataset_dir = Path("texture_extractor/dtd")
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        # Download using kaggle CLI
        subprocess.check_call([
            "kaggle", "datasets", "download", 
            "-d", "jmexpert/describable-textures-dataset-dtd",
            "-p", str(dataset_dir)
        ])
        
        # Extract the downloaded zip file
        zip_file = dataset_dir / "describable-textures-dataset-dtd.zip"
        if zip_file.exists():
            # Create images directory
            images_dir = dataset_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Extract to images directory
            shutil.unpack_archive(str(zip_file), str(images_dir))
            zip_file.unlink()  # Remove the zip file after extraction
            print("Dataset downloaded and extracted successfully!")
            return True
        else:
            print("Error: Downloaded zip file not found")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error downloading dataset: {e}")
        print("\nPlease make sure you have:")
        print("1. Installed the Kaggle API (pip install kaggle)")
        print("2. Set up your Kaggle API credentials in ~/.kaggle/kaggle.json")
        print("3. Set the correct permissions on kaggle.json (chmod 600 ~/.kaggle/kaggle.json)")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main function to set up the DTD dataset."""
    print("=" * 50)
    print("DTD Dataset Setup")
    print("=" * 50)
    
    if download_dtd():
        print("\n✓ DTD dataset setup completed successfully!")
        print("\nYou can now use the texture_emotion_classifier.py script with the DTD dataset.")
    else:
        print("\n✗ Failed to set up DTD dataset.")
        print("\nPlease check your internet connection and try again.")

if __name__ == "__main__":
    main() 