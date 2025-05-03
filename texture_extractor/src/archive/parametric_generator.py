import os
import sys
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from tqdm import tqdm
# import argparse # Removed argparse

class ParametricDesignGenerator:
    """Generates parameters for Rhino/Grasshopper lamp design based on animation data."""
    
    def __init__(self, animation_data_path=None, output_dir="results/parametric_design"):
        """
        Initialize the parametric design generator.
        
        Args:
            animation_data_path (str): Path to animation data JSON (containing displacement grids).
            output_dir (str): Base output directory for parameter files and previews.
        """
        self.animation_data = None
        self.output_dir = output_dir
        
        # Load animation data if provided
        if animation_data_path and os.path.exists(animation_data_path):
            self.load_animation_data(animation_data_path)
        else:
            print(f"Warning: Animation data path not found or not provided: {animation_data_path}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def load_animation_data(self, data_path):
        """Load animation data from JSON file."""
        try:
            with open(data_path, 'r') as f:
                self.animation_data = json.load(f)
            print(f"Loaded animation data with {len(self.animation_data)} time points from {data_path}")
            return self.animation_data
        except Exception as e:
            print(f"Error loading animation data from {data_path}: {e}")
            self.animation_data = None
            return None
    
    def generate_lamp_parameters(self, time_point_index, design_config):
        """Generate parameters for the lamp design at a specific time point using config."""
        if self.animation_data is None:
            print("Error: Animation data not loaded.")
            return None
        
        if not (0 <= time_point_index < len(self.animation_data)):
            print(f"Error: Time point index {time_point_index} out of range (0-{len(self.animation_data)-1}).")
            return None
        
        time_point = self.animation_data[time_point_index]
        emotions = time_point.get("emotions", [])
        # Displacement grid expected to be normalized (0-1) from blender
        displacement_grid_norm = np.array(time_point.get("displacement_grid", [])) 
        
        if displacement_grid_norm.size == 0:
             print(f"Warning: No displacement grid found for time point index {time_point_index}.")
             # Create a flat grid as fallback?
             layers = design_config.get('layers', 32)
             subdivisions = design_config.get('subdivisions', 32)
             displacement_grid_norm = np.zeros((layers, subdivisions)) # Assuming grid is [layers, subdivisions]

        # Base parameters from config
        base_parameters = {
            "radius": design_config.get('base_radius', 100.0),
            "height": design_config.get('base_height', 200.0),
            "thickness": design_config.get('base_thickness', 2.0),
            # Read subdivisions/layers from config, with higher defaults
            "subdivisions": int(design_config.get('subdivisions', 128)), # Ensure int
            "layers": int(design_config.get('layers', 128)),             # Ensure int
            "displacement_scale": design_config.get('displacement_scale', 20.0), # Base scale from config
            "smoothing": design_config.get('smoothing', 0.5),
            "time": time_point.get("time", time_point_index), # Use index if time missing
            "emotions": emotions
        }
        
        # --- Emotion-based Parameter Adjustment ---
        # Simple example: Adjust displacement scale based on primary emotion
        # More complex logic could be added here based on VAD values or multiple emotions
        primary_emotion = emotions[0] if emotions else None
        
        if primary_emotion:
             # Example adjustments (can be refined)
             if primary_emotion in ["joy", "surprised", "excited"]:
                 base_parameters["displacement_scale"] *= 1.3 # More pronounced texture
             elif primary_emotion in ["calm", "peaceful", "serene"]:
                 base_parameters["displacement_scale"] *= 0.7 # Smoother texture
                 base_parameters["smoothing"] = min(1.0, base_parameters["smoothing"] * 1.2) # More smoothing
             elif primary_emotion in ["sad", "fearful"]:
                 base_parameters["displacement_scale"] *= 0.8
                 base_parameters["height"] *= 0.95 # Slightly shorter
             elif primary_emotion in ["angry", "disgusted"]:
                 base_parameters["displacement_scale"] *= 1.5 # Sharper texture?
                 base_parameters["smoothing"] *= 0.8 # Less smoothing

        # --- Displacement Grid Handling ---
        # Apply the main displacement scale to the normalized grid
        # The grid from blender is [grid_y, grid_x] which should map to [layers, subdivisions]
        scaled_displacement = displacement_grid_norm * base_parameters["displacement_scale"]
        
        # Ensure shape matches subdivisions x layers expected by Rhino script/GH definition
        # The original script had grid_to_cylindrical which just returned grid.T essentially.
        # Let's assume the grid from blender is already [layers, subdivisions]
        # If not, it might need transposing: scaled_displacement.T
        # For now, assume shape is correct.
        
        # Add final displacement values to parameters
        base_parameters["displacement_values"] = scaled_displacement.tolist()
        
        return base_parameters
    
    # Removed grid_to_cylindrical as it seemed redundant or needs clarification
    
    def visualize_lamp_3d(self, parameters, output_path=None):
        """Create a 3D visualization preview of the lamp design."""
        # Check if matplotlib is available
        try:
            from mpl_toolkits.mplot3d import Axes3D
        except ImportError:
            print("Warning: matplotlib 3D toolkit not available. Skipping 3D visualization.")
            return

        try:
            radius = parameters["radius"]
            height = parameters["height"]
            # Note: displacement_scale is already applied in generate_lamp_parameters
            # We use the final "displacement_values" which are scaled.
            displacement_values = np.array(parameters["displacement_values"]) 
            
            # Infer subdivisions and layers from the displacement grid shape
            if displacement_values.ndim == 2:
                 layers, subdivisions = displacement_values.shape 
            else: # Handle potential errors or flat arrays
                 print("Warning: Invalid displacement_values shape for visualization.")
                 layers = parameters.get('layers', 32)
                 subdivisions = parameters.get('subdivisions', 32)
                 displacement_values = np.zeros((layers, subdivisions)) # Fallback

            # Create cylindrical coordinates
            theta = np.linspace(0, 2*np.pi, subdivisions + 1) # +1 to close the loop
            z = np.linspace(0, height, layers)
            theta_grid, z_grid = np.meshgrid(theta, z)
            
            # Apply displacement to radius
            # Need to wrap displacement values for the closed loop
            disp_wrapped = np.hstack((displacement_values, displacement_values[:, 0:1]))
            r_grid = radius + disp_wrapped # displacement_values already scaled
            
            # Convert to Cartesian coordinates
            x = r_grid * np.cos(theta_grid)
            y = r_grid * np.sin(theta_grid)
            
            fig = plt.figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection='3d')
            
            # Plot surface
            ax.plot_surface(x, y, z_grid, cmap='viridis', alpha=0.9, rstride=1, cstride=1, linewidth=0.1, edgecolors='k')
            
            # Auto-scaling axes
            max_range = np.array([x.max()-x.min(), y.max()-y.min(), z_grid.max()-z_grid.min()]).max() / 2.0
            mid_x = (x.max()+x.min()) * 0.5; mid_y = (y.max()+y.min()) * 0.5; mid_z = (z_grid.max()+z_grid.min()) * 0.5
            ax.set_xlim(mid_x - max_range, mid_x + max_range)
            ax.set_ylim(mid_y - max_range, mid_y + max_range)
            ax.set_zlim(mid_z - max_range, mid_z + max_range) # Adjust z-axis if needed
            # ax.set_zlim(0, height) # Or fix Z to height

            title = f"Lamp Preview t={parameters['time']:.1f}"
            if parameters['emotions']: title += f"\n{', '.join(parameters['emotions'])}"
            plt.title(title, fontsize=10)
            ax.set_axis_off() # Clean look
            
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                plt.savefig(output_path, dpi=150) # Reasonable DPI for preview
                # print(f"Saved 3D visualization to {output_path}") # Less verbose
            plt.close(fig) # Close plot figure
        except Exception as e:
             print(f"Error during 3D visualization: {e}")
             # Ensure plot is closed if error occurs mid-way
             if 'fig' in locals() and plt.fignum_exists(fig.number): plt.close(fig)

    def save_gh_params(self, parameters, output_path):
        """Save parameter file formatted for Grasshopper (or general use)."""
        # Simple JSON format is usually sufficient
        gh_params = {
            "schema": "lamp_params_v1.0", # Add a version schema
            "metadata": {
                "time": parameters["time"],
                "emotions": parameters["emotions"]
            },
            "parameters": {
                "radius": parameters["radius"],
                "height": parameters["height"],
                "thickness": parameters["thickness"],
                "subdivisions": parameters["subdivisions"],
                "layers": parameters["layers"],
                "displacement_scale_applied": parameters["displacement_scale"], # Record the scale used
                "smoothing": parameters["smoothing"],
                # Store displacement values (already scaled)
                "displacement_values": parameters["displacement_values"] 
            }
        }
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(gh_params, f, indent=2)
            # print(f"Saved parameters to {output_path}") # Less verbose
        except Exception as e:
             print(f"Error saving parameters to {output_path}: {e}")
    
    def process_time_points(self, design_config, visualize=True):
        """Process multiple time points and generate parameters for each."""
        if self.animation_data is None:
            print("Error: Animation data not loaded. Cannot process time points.")
            return None
        
        num_points = len(self.animation_data)
        print(f"Processing {num_points} time points for parametric design (generating only for key moments)...")
        results_summary = []
        last_displacement_grid = None
        generated_count = 0
        
        for i in tqdm(range(num_points), desc="Generating Lamp Designs"):
            current_animation_entry = self.animation_data[i]
            current_displacement_grid = np.array(current_animation_entry.get("displacement_grid", []))

            # Check if displacement grid is valid and different from the last one, or if it's the first/last frame
            should_generate = False
            if current_displacement_grid.size > 0:
                if last_displacement_grid is None or not np.array_equal(current_displacement_grid, last_displacement_grid):
                    should_generate = True
                # Always generate for the first and last frame for completeness
                if i == 0 or i == num_points - 1:
                    should_generate = True
            else:
                print(f"Warning: Skipping frame {i} due to missing displacement grid.")
                continue # Skip if grid is invalid

            if should_generate:
                generated_count += 1
                parameters = self.generate_lamp_parameters(i, design_config)
                if parameters is None: continue # Skip if parameter generation failed

                time_val = parameters["time"]
                emotions_str = "_".join(parameters['emotions']) if parameters['emotions'] else "neutral"
                # Sanitize emotion string for filename
                safe_emotions_str = "".join(c if c.isalnum() else "_" for c in emotions_str)[:20] # Limit length
                time_str = f"{float(time_val):.2f}".replace('.', '_')

                base_filename = f"lamp_params_idx{i:04d}_t{time_str}_{safe_emotions_str}"

                # Save parameters JSON
                param_path = os.path.join(self.output_dir, f"{base_filename}.json")
                self.save_gh_params(parameters, param_path)

                # Visualize if requested
                viz_path = None
                if visualize:
                    viz_path = os.path.join(self.output_dir, f"{base_filename}_preview.png")
                    self.visualize_lamp_3d(parameters, viz_path)

                results_summary.append({
                    "index": i,
                    "time": time_val,
                    "emotions": parameters["emotions"],
                    "parameters_path": param_path,
                    "preview_path": viz_path if visualize else None
                })
                # Update the last grid
                last_displacement_grid = current_displacement_grid
            # else: # Optional: Log skipped frames
                # print(f"Skipping frame {i} - displacement grid unchanged.")

        print(f"Finished processing. Generated {generated_count} key moment lamp designs.")
        return results_summary
    
    def generate_rhino_python_script(self, parameters_path, output_path=None):
        """Generate a Python script for Rhino to create the lamp model from a params file."""
        # Define the template string with named parameter {parameters_path}
        # All other braces in the template are escaped as double braces {{}}
        script_template = '''
import rhinoscriptsyntax as rs
import Rhino
import json
import math
import os

# --- Configuration ---
PARAMS_FILE = r"{parameters_path}" 
OUTPUT_LAYER = "GeneratedLamp"
SAVE_FILE = True # Set to False to disable auto-saving

# --- Helper Functions ---
def load_parameters(filepath):
    """Load lamp parameters from JSON file."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        # Extract parameters from the nested structure
        if "parameters" in data:
            return data["parameters"]
        else:
            print("Error: 'parameters' key not found in JSON data.")
            return None
    except Exception as e:
        print("Error loading parameters file: {{}}".format(e))
        return None

def create_lamp_surface(params):
    """Create the outer NURBS surface based on parameters."""
    radius = params.get("radius", 100.0)
    height = params.get("height", 200.0)
    subdivisions = params.get("subdivisions", 32)
    layers = params.get("layers", 32)
    # displacement_values are already scaled in the JSON
    displacement_values = params.get("displacement_values", []) 

    if not displacement_values or len(displacement_values) != layers or len(displacement_values[0]) != subdivisions:
         print("Error: Invalid or missing displacement_values. Creating base cylinder.")
         # Create a simple cylinder surface as fallback
         plane = rs.WorldXYPlane()
         circle = rs.AddCircle(plane, radius)
         path_line = rs.AddLine((0,0,0), (0,0,height))
         surface = rs.AddSweep1(path_line, circle)
         rs.DeleteObject(path_line)
         rs.DeleteObject(circle)
         return surface

    # Create points for the outer surface
    points = []
    for i in range(layers): # Z-axis (height)
        z = i * height / (layers - 1)
        layer_points = []
        for j in range(subdivisions): # Theta (angle)
            angle = j * 2.0 * math.pi / subdivisions
            # Get displacement for this point (i=layer, j=subdivision)
            displacement = displacement_values[i][j] 
            r = radius + displacement
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            layer_points.append(rs.AddPoint(x, y, z)) # Add Rhino points directly
        # Add start point again to close the loop for NURBS surface U-direction
        layer_points.append(layer_points[0]) 
        points.append(layer_points)
    
    # Create NURBS surface (U=subdivisions+1, V=layers)
    # Degree 3 is common for smooth surfaces
    surface = rs.AddNurbsSurface(
        (subdivisions + 1, layers), # Point counts in U, V
        [p for layer in points for p in layer], # Flattened list of points
        (3, 3), # Degree in U, V
        (False, False) # Not periodic in U, V (closed manually) 
                       # Might need True in U if points list wasn't closed
    )
    
    # Clean up temporary points
    for layer in points: rs.DeleteObjects(layer) 
    
    return surface

# --- Main Script Logic ---
def run():
    # Load parameters
    params = load_parameters(PARAMS_FILE)
    if not params: return

    # Ensure output layer exists
    if not rs.IsLayer(OUTPUT_LAYER): rs.AddLayer(OUTPUT_LAYER)
    rs.CurrentLayer(OUTPUT_LAYER)
    
    # Create outer surface
    print("Creating outer surface...")
    outer_surface = create_lamp_surface(params)
    if not outer_surface: 
        print("Failed to create outer surface.")
        return

    # Create inner surface (offset)
    thickness = params.get("thickness", 2.0)
    print("Creating inner surface (offsetting by {{0}})...".format(-thickness))
    # OffsetSurface might fail for complex shapes, add error handling
    inner_surface = rs.OffsetSurface(outer_surface, -thickness, tolerance=rs.UnitAbsoluteTolerance()) 
    if not inner_surface:
         print("Warning: OffsetSurface failed. Inner surface not created.")
         # Decide how to proceed: maybe just keep outer surface?
         # For now, we'll stop if offset fails for a solid.
         rs.DeleteObject(outer_surface)
         return

    # Attempt to create caps and join into a solid
    print("Creating caps and joining surfaces...")
    try:
        # Get borders (might need adjustment based on surface orientation)
        borders = rs.DuplicateSurfaceBorder(outer_surface)
        if not borders or len(borders) < 2: raise Exception("Could not get surface borders.")
        
        # Assuming bottom is index 0, top is index 1 (adjust if needed)
        bottom_curve = borders[0] 
        top_curve = borders[1] 
        
        # Create planar surfaces for caps
        bottom_cap = rs.AddPlanarSrf(bottom_curve)
        top_cap = rs.AddPlanarSrf(top_curve)
        
        if not bottom_cap or not top_cap: raise Exception("Could not create cap surfaces.")
        
        # Join all surfaces
        surfaces_to_join = [outer_surface, inner_surface, bottom_cap[0], top_cap[0]] # PlanarSrf returns list
        lamp_solid = rs.JoinSurfaces(surfaces_to_join, delete_input=True) # Delete intermediate surfaces
        
        if not lamp_solid or len(lamp_solid) != 1: raise Exception("Failed to join surfaces into a single solid.")
        
        print("Successfully created lamp solid.")
        final_object = lamp_solid[0]
        
    except Exception as e:
        print("Error creating solid: {{0}}".format(e))
        print("Keeping outer and inner surfaces separately.")
        # Keep outer and inner if join fails
        final_object = [outer_surface, inner_surface] 

    # Optional: Save the Rhino file
    if SAVE_FILE:
        output_3dm = PARAMS_FILE.replace(".json", ".3dm")
        # Ensure filename is valid
        output_3dm = os.path.basename(output_3dm) 
        output_3dm = "".join(c if c.isalnum() or c in ('_', '.', '-') else '_' for c in output_3dm)
        output_3dm_path = os.path.join(os.path.dirname(PARAMS_FILE), output_3dm)
        
        print("Saving Rhino file to: {{0}}".format(output_3dm_path))
        # Use indexed format placeholders for .format() calls
        rs.Command('_-Save "{{0}}" _Enter'.format(output_3dm_path))

    print("Script finished.")

# --- Run the script ---
if __name__ == "__main__":
    run()
''' # End of template string
        
        # Default output path if not provided
        if output_path is None:
            script_dir = os.path.dirname(parameters_path)
            filename = os.path.basename(parameters_path).replace(".json", "_rhino.py")
            output_path = os.path.join(script_dir, filename)
        
        # Use .format() with named parameter for the outer template substitution
        script_content = script_template.format(parameters_path=parameters_path.replace("\\", "/"))
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(script_content)
            print(f"Generated Rhino Python script: {output_path}")
            return output_path
        except Exception as e:
             print(f"Error generating Rhino script {output_path}: {e}")
             return None

# Removed the main() function and if __name__ == "__main__": block
# Class methods are now intended to be called by main.py
