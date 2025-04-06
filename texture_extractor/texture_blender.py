import os
import sys
import numpy as np
import json
import cv2
from PIL import Image
from tqdm import tqdm
import matplotlib.pyplot as plt

class TextureBlender:
    """Blends textures based on emotional weights and generates displacement maps."""
    
    def __init__(self, texture_timeline_path=None, output_dir="results/blended_textures"):
        """
        Initialize the texture blender.
        
        Args:
            texture_timeline_path: Path to texture timeline JSON
            output_dir: Output directory for blended textures
        """
        self.texture_timeline = None
        self.output_dir = output_dir
        
        # Load texture timeline if provided
        if texture_timeline_path and os.path.exists(texture_timeline_path):
            self.load_texture_timeline(texture_timeline_path)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "textures"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "displacement_maps"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "previews"), exist_ok=True)
    
    def load_texture_timeline(self, timeline_path):
        """Load texture timeline from JSON file."""
        with open(timeline_path, 'r') as f:
            self.texture_timeline = json.load(f)
        print(f"Loaded texture timeline with {len(self.texture_timeline)} time points")
        return self.texture_timeline
    
    def preprocess_texture(self, texture_path, target_size=(512, 512), grayscale=True):
        """Load and preprocess a texture image."""
        # Handle invalid paths
        if texture_path is None or not os.path.exists(texture_path):
            print(f"Warning: Texture path does not exist: {texture_path}")
            # Return a default texture (gray image)
            if grayscale:
                return np.ones(target_size, dtype=np.uint8) * 128
            else:
                return np.ones((*target_size, 3), dtype=np.uint8) * 128
        
        # Load image
        try:
            img = cv2.imread(texture_path)
            if img is None:
                raise ValueError(f"Failed to load image: {texture_path}")
            
            # Convert to grayscale if requested
            if grayscale:
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                # Convert BGR to RGB
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Resize to target size
            img = cv2.resize(img, target_size)
            
            return img
        
        except Exception as e:
            print(f"Error processing texture {texture_path}: {e}")
            # Return a default texture (gray image)
            if grayscale:
                return np.ones(target_size, dtype=np.uint8) * 128
            else:
                return np.ones((*target_size, 3), dtype=np.uint8) * 128
    
    def blend_textures(self, texture_paths, weights, target_size=(512, 512), grayscale=True):
        """Blend multiple textures using weighted average."""
        if not texture_paths:
            return None
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights] if total_weight > 0 else [1.0 / len(weights)] * len(weights)
        
        # Initialize blended image
        blended = np.zeros(target_size if grayscale else (*target_size, 3), dtype=np.float32)
        
        # Blend textures
        valid_count = 0
        for i, (path, weight) in enumerate(zip(texture_paths, weights)):
            img = self.preprocess_texture(path, target_size, grayscale)
            if img is not None:
                valid_count += 1
                blended += img.astype(np.float32) * weight
        
        if valid_count == 0:
            print("Warning: No valid textures to blend.")
            return None
        
        # Convert to 8-bit image
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        
        return blended
    
    def create_displacement_map(self, texture, blur_kernel=5, scale=1.0):
        """Create a displacement map from a texture."""
        # Ensure grayscale
        if len(texture.shape) == 3:
            texture = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to smooth the texture
        if blur_kernel > 0:
            texture = cv2.GaussianBlur(texture, (blur_kernel, blur_kernel), 0)
        
        # Scale displacement values (0-255)
        displacement = texture.astype(np.float32) * scale / 255.0
        
        # Normalize to 0-1 range
        displacement = (displacement - displacement.min()) / (displacement.max() - displacement.min() + 1e-8)
        
        # Convert back to 8-bit image
        displacement = (displacement * 255).astype(np.uint8)
        
        return displacement
    
    def create_preview(self, texture, displacement, output_path=None):
        """Create a side-by-side preview of texture and displacement map."""
        # Convert to RGB if not already
        if len(texture.shape) == 2:
            texture_rgb = cv2.cvtColor(texture, cv2.COLOR_GRAY2RGB)
        else:
            texture_rgb = texture.copy()
        
        # Create a colormap for the displacement map
        displacement_colored = cv2.applyColorMap(displacement, cv2.COLORMAP_JET)
        displacement_rgb = cv2.cvtColor(displacement_colored, cv2.COLOR_BGR2RGB)
        
        # Create a side-by-side image
        preview = np.hstack((texture_rgb, displacement_rgb))
        
        # Save preview if output path is provided
        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))
        
        return preview
    
    def process_timeline(self, target_size=(512, 512), blur_kernel=5, displacement_scale=1.0):
        """Process the timeline to generate blended textures and displacement maps."""
        if self.texture_timeline is None:
            raise ValueError("Texture timeline not loaded.")
        
        results = []
        
        for i, entry in enumerate(tqdm(self.texture_timeline, desc="Processing timeline")):
            time_point = entry["time"]
            emotions = entry["emotions"]
            textures = entry["textures"]
            
            # Skip if no textures
            if not textures:
                print(f"Warning: No textures for time point {time_point}. Skipping.")
                continue
            
            # Extract texture paths and weights
            texture_paths = [t["texture_path"] for t in textures]
            weights = [t["weight"] for t in textures]
            
            # Blend textures
            blended = self.blend_textures(texture_paths, weights, target_size)
            if blended is None:
                print(f"Warning: Failed to blend textures for time point {time_point}. Skipping.")
                continue
            
            # Create displacement map
            displacement = self.create_displacement_map(blended, blur_kernel, displacement_scale)
            
            # Generate filenames
            texture_filename = f"texture_{i:04d}_t{float(time_point):.1f}.png"
            displacement_filename = f"displace_{i:04d}_t{float(time_point):.1f}.png"
            preview_filename = f"preview_{i:04d}_t{float(time_point):.1f}.png"
            
            # Save blended texture
            texture_path = os.path.join(self.output_dir, "textures", texture_filename)
            cv2.imwrite(texture_path, blended)
            
            # Save displacement map
            displacement_path = os.path.join(self.output_dir, "displacement_maps", displacement_filename)
            cv2.imwrite(displacement_path, displacement)
            
            # Create and save preview
            preview_path = os.path.join(self.output_dir, "previews", preview_filename)
            self.create_preview(blended, displacement, preview_path)
            
            # Add to results
            results.append({
                "time": time_point,
                "emotions": emotions,
                "texture_path": texture_path,
                "displacement_path": displacement_path,
                "preview_path": preview_path
            })
        
        # Save results to JSON
        results_path = os.path.join(self.output_dir, "blending_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Processed {len(results)} time points. Results saved to {results_path}")
        
        return results
    
    def create_summary_visualization(self, results, output_path=None):
        """Create a summary visualization of blended textures and displacement maps."""
        if not results:
            print("Warning: No results to visualize.")
            return
        
        # Determine grid size
        n_samples = min(len(results), 16)  # Show at most 16 samples
        grid_size = int(np.ceil(np.sqrt(n_samples)))
        
        # Create figure
        fig, axes = plt.subplots(grid_size, grid_size, figsize=(15, 15))
        axes = axes.flatten()
        
        # Select samples at regular intervals
        step = max(1, len(results) // n_samples)
        samples = results[::step][:n_samples]
        
        for i, sample in enumerate(samples):
            if i >= len(axes):
                break
                
            # Load preview image
            preview_path = sample["preview_path"]
            if os.path.exists(preview_path):
                img = cv2.imread(preview_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # Display image
                axes[i].imshow(img)
                axes[i].set_title(f"t={sample['time']:.1f}s\n{', '.join(sample['emotions'])}")
                axes[i].axis('off')
        
        # Hide unused subplots
        for i in range(len(samples), len(axes)):
            axes[i].axis('off')
        
        plt.tight_layout()
        
        # Save figure if output path is provided
        if output_path:
            plt.savefig(output_path)
            print(f"Saved summary visualization to {output_path}")
        
        plt.close()
    
    def create_animation_data(self, results, output_path=None):
        """Create animation data for parametric design."""
        if not results:
            print("Warning: No results to create animation data from.")
            return
        
        animation_data = []
        
        for result in results:
            # Load displacement map
            displacement_path = result["displacement_path"]
            if os.path.exists(displacement_path):
                # Downsample displacement map for animation data
                displacement = cv2.imread(displacement_path, cv2.IMREAD_GRAYSCALE)
                h, w = displacement.shape
                
                # Downsample to 32x32 grid (or similar manageable size for parametric design)
                grid_size = 32
                step_y, step_x = h // grid_size, w // grid_size
                grid = np.zeros((grid_size, grid_size), dtype=np.float32)
                
                for y in range(grid_size):
                    for x in range(grid_size):
                        # Average displacement values in this grid cell
                        y1, y2 = y * step_y, (y + 1) * step_y
                        x1, x2 = x * step_x, (x + 1) * step_x
                        grid[y, x] = displacement[y1:y2, x1:x2].mean() / 255.0
                
                # Add to animation data
                animation_data.append({
                    "time": result["time"],
                    "emotions": result["emotions"],
                    "displacement_grid": grid.tolist()
                })
        
        # Save animation data to JSON
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(animation_data, f, indent=2)
            print(f"Saved animation data to {output_path}")
        
        return animation_data

# Function to run the blender from command line
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Blend textures based on emotion timeline")
    parser.add_argument("--timeline", type=str, required=True, help="Path to texture timeline JSON")
    parser.add_argument("--output_dir", type=str, default="results/blended_textures", help="Output directory")
    parser.add_argument("--size", type=int, default=512, help="Target size for blended textures")
    parser.add_argument("--blur", type=int, default=5, help="Blur kernel size for displacement maps")
    parser.add_argument("--scale", type=float, default=1.0, help="Displacement scale factor")
    args = parser.parse_args()
    
    blender = TextureBlender(args.timeline, args.output_dir)
    results = blender.process_timeline(
        target_size=(args.size, args.size),
        blur_kernel=args.blur,
        displacement_scale=args.scale
    )
    
    # Create summary visualization
    summary_path = os.path.join(args.output_dir, "summary_visualization.png")
    blender.create_summary_visualization(results, summary_path)
    
    # Create animation data
    animation_path = os.path.join(args.output_dir, "animation_data.json")
    blender.create_animation_data(results, animation_path)

if __name__ == "__main__":
    main() 