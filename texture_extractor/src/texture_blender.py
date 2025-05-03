import os
import sys
import numpy as np
import json
import cv2
from PIL import Image
from tqdm import tqdm
import matplotlib.pyplot as plt
from collections import defaultdict # Added for summary visualization
from utils import detect_dataset_type, get_normal_map_path, is_normal_map_available

class TextureBlender:
    """Blends textures based on emotional weights and generates displacement maps."""
    
    def __init__(self, texture_timeline_path=None, output_dir="results/blended_textures"):
        """
        Initialize the texture blender.
        
        Args:
            texture_timeline_path (str): Path to texture timeline JSON.
            output_dir (str): Base output directory for blended textures, maps, etc.
        """
        self.texture_timeline = None
        self.output_dir = output_dir
        self.textures_output_dir = os.path.join(output_dir, "textures")
        self.displace_output_dir = os.path.join(output_dir, "displacement_maps")
        self.previews_output_dir = os.path.join(output_dir, "previews")
        
        # Load texture timeline if provided
        if texture_timeline_path and os.path.exists(texture_timeline_path):
            self.load_texture_timeline(texture_timeline_path)
        else:
             print(f"Warning: Texture timeline path not found or not provided: {texture_timeline_path}")

        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.textures_output_dir, exist_ok=True)
        os.makedirs(self.displace_output_dir, exist_ok=True)
        os.makedirs(self.previews_output_dir, exist_ok=True)
    
    def load_texture_timeline(self, timeline_path):
        """Load texture timeline from JSON file."""
        try:
            with open(timeline_path, 'r') as f:
                self.texture_timeline = json.load(f)
            print(f"Loaded texture timeline with {len(self.texture_timeline)} time points from {timeline_path}")
            return self.texture_timeline
        except Exception as e:
            print(f"Error loading texture timeline from {timeline_path}: {e}")
            self.texture_timeline = None
            return None
    
    def preprocess_texture(self, texture_path, target_size=(512, 512), grayscale=True):
        """Load and preprocess a texture image."""
        if texture_path is None or not os.path.exists(texture_path):
            print(f"Warning: Texture path does not exist: {texture_path}. Returning default gray image.")
            default_shape = target_size if grayscale else (*target_size, 3)
            return np.ones(default_shape, dtype=np.uint8) * 128
        
        try:
            img = cv2.imread(texture_path)
            if img is None: raise ValueError(f"cv2.imread failed for {texture_path}")
            
            if grayscale:
                if len(img.shape) == 3: img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            elif len(img.shape) == 3: # Ensure RGB if color requested
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            img = cv2.resize(img, target_size, interpolation=cv2.INTER_LANCZOS4) # Use high quality resize
            return img
        
        except Exception as e:
            print(f"Error processing texture {texture_path}: {e}. Returning default gray image.")
            default_shape = target_size if grayscale else (*target_size, 3)
            return np.ones(default_shape, dtype=np.uint8) * 128
    
    def blend_textures(self, texture_paths, weights, target_size=(512, 512), grayscale=True):
        """Blend multiple textures using weighted average."""
        if not texture_paths: return None
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight <= 0: weights = [1.0 / len(weights)] * len(weights)
        else: weights = [w / total_weight for w in weights]
        
        blended = np.zeros(target_size if grayscale else (*target_size, 3), dtype=np.float32)
        valid_count = 0
        
        for path, weight in zip(texture_paths, weights):
            img = self.preprocess_texture(path, target_size, grayscale)
            if img is not None: # Check if preprocessing succeeded
                valid_count += 1
                blended += img.astype(np.float32) * weight
        
        if valid_count == 0:
            print("Warning: No valid textures found to blend.")
            return None
        
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        return blended
    
    def create_displacement_map(self, texture, blur_kernel=5, scale=1.0, texture_path=None):
        """
        Create a displacement map from a texture.
        If texture_path is provided and is from huggingface dataset, use the existing normal map.
        """
        # Check if we can use an existing normal map
        if texture_path and detect_dataset_type(texture_path) == 'huggingface':
            normal_map_path = get_normal_map_path(texture_path)
            if normal_map_path and os.path.exists(normal_map_path):
                try:
                    # Load and process the normal map
                    normal_map = cv2.imread(normal_map_path, cv2.IMREAD_GRAYSCALE)
                    if normal_map is not None:
                        # Process the normal map if needed
                        return normal_map
                except Exception as e:
                    print(f"Error loading normal map {normal_map_path}: {e}. Falling back to generated map.")
        
        # Fall back to generating a displacement map from the texture
        if len(texture.shape) == 3:
            texture = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY)
        
        # Ensure blur kernel is odd and positive, or 0
        blur_kernel = int(blur_kernel)
        if blur_kernel > 0 and blur_kernel % 2 == 0:
             blur_kernel += 1 # Make it odd
             print(f"Adjusted blur kernel to be odd: {blur_kernel}")
        
        if blur_kernel > 0:
            blurred_texture = cv2.GaussianBlur(texture, (blur_kernel, blur_kernel), 0)
        else:
            blurred_texture = texture # No blur

        # Scale displacement values (0-255) -> (0-scale)
        displacement = blurred_texture.astype(np.float32) * scale / 255.0
        
        # Normalize to 0-1 range (optional, depends on how it's used later)
        # If scale is meant to be absolute, don't normalize here.
        # If scale is relative, normalize. Let's assume relative for now.
        min_val, max_val = displacement.min(), displacement.max()
        if max_val - min_val > 1e-8:
             displacement = (displacement - min_val) / (max_val - min_val)
        else: # Handle flat displacement map
             displacement = np.zeros_like(displacement, dtype=np.float32)

        # Convert back to 8-bit image for saving
        displacement_8bit = (displacement * 255).astype(np.uint8)
        return displacement_8bit

    def create_preview(self, texture_color, displacement_gray, normal_map_gray, output_path=None):
        """Create a side-by-side preview of color texture, displacement map, and normal map."""
        try:
            # Ensure texture is RGB
            if len(texture_color.shape) == 2:
                texture_rgb = cv2.cvtColor(texture_color, cv2.COLOR_GRAY2RGB)
            elif texture_color.shape[2] == 1: # Handle single channel color image?
                 texture_rgb = cv2.cvtColor(texture_color, cv2.COLOR_GRAY2RGB)
            else:
                texture_rgb = texture_color.copy() # Assume RGB

            # Colorize displacement map (Viridis)
            displacement_colored = cv2.applyColorMap(displacement_gray, cv2.COLORMAP_VIRIDIS)
            displacement_rgb = cv2.cvtColor(displacement_colored, cv2.COLOR_BGR2RGB)

            # Ensure normal map is RGB for stacking (if it exists)
            if normal_map_gray is not None:
                if len(normal_map_gray.shape) == 2:
                    normal_map_rgb = cv2.cvtColor(normal_map_gray, cv2.COLOR_GRAY2RGB)
                else:
                     normal_map_rgb = normal_map_gray.copy() # Assume it's already displayable
                # Stack all three
                preview = np.hstack((texture_rgb, displacement_rgb, normal_map_rgb))
            else:
                # Stack only texture and displacement if normal map is missing
                # Create a placeholder for normal map?
                placeholder_shape = list(texture_rgb.shape)
                placeholder_shape[1] = texture_rgb.shape[1] # Match width
                normal_placeholder = np.ones(placeholder_shape, dtype=np.uint8) * 128 # Gray placeholder
                cv2.putText(normal_placeholder, 'No Normal Map', (10, placeholder_shape[0]//2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2)
                preview = np.hstack((texture_rgb, displacement_rgb, normal_placeholder))


            if output_path:
                # Ensure directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                # Save as BGR
                cv2.imwrite(output_path, cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))
            return preview
        except Exception as e:
            print(f"Error creating preview image: {e}")
            return None

    def process_timeline(self, target_size=(512, 512), blur_kernel=5, displacement_scale=1.0, displacement_scale_multiplier=2.0): # Added multiplier
        """Process the timeline to generate blended textures and displacement maps."""
        print(f"Using displacement scale: {displacement_scale}, multiplier: {displacement_scale_multiplier}") # Log scale info
        if self.texture_timeline is None:
            print("Error: Texture timeline not loaded.")
            return None # Return None instead of raising error
        
        results = []
        print(f"Processing texture timeline ({len(self.texture_timeline)} points)...")
        
        for i, entry in enumerate(tqdm(self.texture_timeline, desc="Blending Textures")):
            time_point = entry.get("time", i) # Use index if time missing
            emotions = entry.get("emotions", [])
            textures_info = entry.get("textures", [])
            
            if not textures_info:
                print(f"Warning: No textures for time point {time_point}. Skipping.")
                continue

            # --- Updated logic for single texture per time point ---
            if len(textures_info) != 1:
                 print(f"Warning: Expected 1 texture info entry for time {time_point}, found {len(textures_info)}. Using the first.")
                 # Continue anyway, using the first texture if available

            texture_info = textures_info[0]
            texture_path = texture_info.get("texture_path")

            if not texture_path:
                 print(f"Warning: No texture path found for time point {time_point}. Skipping.")
                 continue

            # Load the single texture (grayscale for displacement)
            texture_gray = self.preprocess_texture(texture_path, target_size, grayscale=True)
            if texture_gray is None:
                 print(f"Warning: Failed to load texture {texture_path} for time point {time_point}. Skipping.")
                 continue

            # Create displacement map from the single texture or use existing normal map
            # Use a potentially larger scale for visibility, now configurable
            effective_displacement_scale = displacement_scale * displacement_scale_multiplier # Use multiplier
            displacement = self.create_displacement_map(
                texture_gray,
                blur_kernel,
                effective_displacement_scale, # Use the increased scale
                texture_path # Pass the actual path for normal map check
            )

            # Load the texture in color for preview
            texture_color = self.preprocess_texture(texture_path, target_size, grayscale=False)
            if texture_color is None: texture_color = cv2.cvtColor(texture_gray, cv2.COLOR_GRAY2RGB) # Fallback

            # Generate filenames
            time_str = f"{float(time_point):.2f}".replace('.', '_') # Format time for filename
            # Use a more descriptive name if possible (e.g., from keywords)
            keywords_str = "_".join(entry.get("keywords", [])).replace(" ", "")[:30] # Limit length
            base_filename = f"{i:04d}_t{time_str}_{keywords_str}"
            texture_filename = f"{base_filename}_texture.png"
            displacement_filename = f"{base_filename}_displace.png"
            preview_filename = f"{base_filename}_preview.png"

            # Define full output paths
            output_texture_path = os.path.join(self.textures_output_dir, texture_filename)
            output_displacement_path = os.path.join(self.displace_output_dir, displacement_filename)
            output_preview_path = os.path.join(self.previews_output_dir, preview_filename)

            # Save outputs
            try: cv2.imwrite(output_texture_path, texture_gray) # Save grayscale texture
            except Exception as e: print(f"Error saving texture {output_texture_path}: {e}")
            try: cv2.imwrite(output_displacement_path, displacement)
            except Exception as e: print(f"Error saving displacement map {output_displacement_path}: {e}")

            # Load normal map if available
            normal_map_path = None
            normal_map_gray = None
            if detect_dataset_type(texture_path) == 'huggingface':
                normal_map_path = get_normal_map_path(texture_path)
                if normal_map_path and os.path.exists(normal_map_path):
                    try:
                        normal_map_gray = cv2.imread(normal_map_path, cv2.IMREAD_GRAYSCALE)
                        if normal_map_gray is not None:
                             normal_map_gray = cv2.resize(normal_map_gray, target_size, interpolation=cv2.INTER_LANCZOS4)
                        else: print(f"Warning: Failed to load normal map {normal_map_path}")
                    except Exception as e: print(f"Error loading normal map {normal_map_path}: {e}")

            # Create and save preview (passing color texture, gray displacement, gray normal)
            self.create_preview(texture_color, displacement, normal_map_gray, output_preview_path)

            # Store original retrieved path and generated paths
            results.append({
                "time": time_point,
                "emotions": entry.get("vad_quadrant", "unknown"), # Use quadrant for simplicity
                "keywords": entry.get("keywords", []),
                "clip_prompt": entry.get("clip_prompt", ""),
                "retrieved_texture_path": texture_path, # Original path from CLIP
                "texture_path": output_texture_path, # Path to saved grayscale texture
                "displacement_path": output_displacement_path,
                "preview_path": output_preview_path
            })
        
        print(f"Finished processing timeline. Generated {len(results)} sets of outputs.")
        return results
    
    def create_summary_visualization(self, results, output_path=None):
        """Create a summary visualization grid of previews."""
        if not results:
            print("Warning: No results to create summary visualization.")
            return
        
        n_samples = min(len(results), 16)
        if n_samples == 0: return
        
        grid_size = int(np.ceil(np.sqrt(n_samples)))
        fig, axes = plt.subplots(grid_size, grid_size, figsize=(15, 15))
        if n_samples == 1: axes = np.array([axes]) # Make iterable
        axes = axes.flatten()
        
        step = max(1, len(results) // n_samples)
        samples_to_plot = results[::step][:n_samples]
        
        print(f"Creating summary visualization with {len(samples_to_plot)} samples...")
        
        for i, sample in enumerate(samples_to_plot):
            preview_path = sample.get("preview_path")
            if preview_path and os.path.exists(preview_path):
                try:
                    img = cv2.imread(preview_path)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # Convert BGR to RGB for plt
                    axes[i].imshow(img)
                    title = f"t={sample.get('time', i):.1f}s"
                    emotions = sample.get('emotions', [])
                    if emotions: title += f"\n{', '.join(emotions)}"
                    axes[i].set_title(title, fontsize=8)
                    axes[i].axis('off')
                except Exception as e:
                    print(f"Error loading preview {preview_path}: {e}")
                    axes[i].text(0.5, 0.5, "Error", ha='center', va='center'); axes[i].axis('off')
            else:
                axes[i].text(0.5, 0.5, "No Preview", ha='center', va='center'); axes[i].axis('off')
        
        for i in range(len(samples_to_plot), len(axes)): axes[i].axis('off') # Hide unused
        
        plt.tight_layout()
        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                plt.savefig(output_path, dpi=150) # Lower DPI for summary
                print(f"Saved summary visualization to {output_path}")
            except Exception as e: print(f"Error saving summary visualization: {e}")
        plt.close(fig)
    
    def create_animation_data(self, results, output_path=None, grid_size=32):
        """Create downsampled displacement grid data for animation/parametric design."""
        if not results:
            print("Warning: No results to create animation data from.")
            return None
        
        animation_data = []
        print(f"Creating animation data (downsampling displacement maps to {grid_size}x{grid_size})...")
        
        for result in tqdm(results, desc="Generating Animation Data"):
            displacement_path = result.get("displacement_path")
            if displacement_path and os.path.exists(displacement_path):
                try:
                    displacement = cv2.imread(displacement_path, cv2.IMREAD_GRAYSCALE)
                    if displacement is None: raise ValueError("imread failed")
                    
                    h, w = displacement.shape
                    # Resize using INTER_AREA for downsampling
                    grid = cv2.resize(displacement, (grid_size, grid_size), interpolation=cv2.INTER_AREA)
                    
                    # Normalize grid values to 0-1 float
                    grid_float = grid.astype(np.float32) / 255.0
                    
                    animation_data.append({
                        "time": result.get("time"),
                        "emotions": result.get("emotions", []),
                        "displacement_grid": grid_float.tolist() # Convert to list for JSON
                    })
                except Exception as e:
                    print(f"Error processing displacement map {displacement_path} for animation: {e}")
            else:
                 print(f"Warning: Displacement map not found for time {result.get('time')}. Skipping animation data point.")

        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(animation_data, f, indent=2) # Use indent for readability
                print(f"Saved animation data ({len(animation_data)} points) to {output_path}")
            except Exception as e:
                print(f"Error saving animation data to {output_path}: {e}")
        
        return animation_data

# Removed the main() function and if __name__ == "__main__": block
# Class methods are now intended to be called by main.py
