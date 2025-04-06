import os
import sys
import json
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from tqdm import tqdm

class ParametricDesignGenerator:
    """Generates parameters for Rhino/Grasshopper lamp design."""
    
    def __init__(self, animation_data_path=None, output_dir="results/parametric_design"):
        """
        Initialize the parametric design generator.
        
        Args:
            animation_data_path: Path to animation data JSON
            output_dir: Output directory for parameter files
        """
        self.animation_data = None
        self.output_dir = output_dir
        
        # Load animation data if provided
        if animation_data_path and os.path.exists(animation_data_path):
            self.load_animation_data(animation_data_path)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def load_animation_data(self, data_path):
        """Load animation data from JSON file."""
        with open(data_path, 'r') as f:
            self.animation_data = json.load(f)
        print(f"Loaded animation data with {len(self.animation_data)} time points")
        return self.animation_data
    
    def generate_lamp_parameters(self, time_point_index=None):
        """Generate parameters for the lamp design at a specific time point."""
        if self.animation_data is None:
            raise ValueError("Animation data not loaded.")
        
        # Select time point (default to first if not specified)
        if time_point_index is None:
            time_point_index = 0
        
        if time_point_index >= len(self.animation_data):
            raise ValueError(f"Time point index {time_point_index} out of range (max {len(self.animation_data)-1}).")
        
        time_point = self.animation_data[time_point_index]
        emotions = time_point["emotions"]
        displacement_grid = np.array(time_point["displacement_grid"])
        
        # Base parameters
        base_parameters = {
            "radius": 100.0,  # Base radius in mm
            "height": 200.0,  # Base height in mm
            "thickness": 2.0,  # Wall thickness in mm
            "subdivisions": 32,  # Number of subdivisions
            "layers": 32,      # Number of vertical layers
            "displacement_scale": 20.0,  # Maximum displacement in mm
            "smoothing": 0.5,   # Smoothing factor (0-1)
            "time": time_point["time"],
            "emotions": emotions
        }
        
        # Adjust parameters based on emotions
        for emotion in emotions:
            if emotion == "joy" or emotion == "surprised":
                base_parameters["radius"] *= 1.2
                base_parameters["displacement_scale"] *= 1.3
                base_parameters["smoothing"] *= 0.8
            elif emotion == "calm" or emotion == "peaceful" or emotion == "serene":
                base_parameters["height"] *= 1.1
                base_parameters["displacement_scale"] *= 0.7
                base_parameters["smoothing"] *= 1.3
            elif emotion == "sad":
                base_parameters["height"] *= 0.9
                base_parameters["displacement_scale"] *= 0.6
                base_parameters["smoothing"] *= 1.5
            elif emotion == "angry" or emotion == "fearful" or emotion == "disgusted":
                base_parameters["radius"] *= 0.8
                base_parameters["displacement_scale"] *= 1.5
                base_parameters["smoothing"] *= 0.6
        
        # Convert displacement grid to cylindrical coordinates
        cylindrical_displacement = self.grid_to_cylindrical(displacement_grid)
        
        # Add displacement values to parameters
        base_parameters["displacement_values"] = cylindrical_displacement.tolist()
        
        return base_parameters
    
    def grid_to_cylindrical(self, grid):
        """Convert a 2D displacement grid to cylindrical coordinates."""
        height, width = grid.shape
        
        # Create cylindrical displacement array (subdivisions x layers)
        cylindrical = np.zeros((width, height), dtype=np.float32)
        
        # Map grid to cylinder
        for i in range(height):
            for j in range(width):
                # Straight mapping (width = circumference, height = height)
                cylindrical[j, i] = grid[i, j]
        
        return cylindrical
    
    def visualize_lamp_3d(self, parameters, output_path=None):
        """Create a 3D visualization of the lamp design."""
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        
        # Extract parameters
        radius = parameters["radius"]
        height = parameters["height"]
        displacement_scale = parameters["displacement_scale"]
        displacement_values = np.array(parameters["displacement_values"])
        subdivisions, layers = displacement_values.shape
        
        # Create cylindrical coordinates
        theta = np.linspace(0, 2*np.pi, subdivisions)
        z = np.linspace(0, height, layers)
        theta_grid, z_grid = np.meshgrid(theta, z)
        
        # Apply displacement to radius
        r_grid = radius + displacement_scale * displacement_values.T
        
        # Convert to Cartesian coordinates
        x = r_grid * np.cos(theta_grid)
        y = r_grid * np.sin(theta_grid)
        
        # Create 3D plot
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot surface
        surface = ax.plot_surface(x, y, z_grid, cmap='viridis', alpha=0.8)
        
        # Customize plot
        max_range = max(np.max(x) - np.min(x), np.max(y) - np.min(y), np.max(z_grid) - np.min(z_grid)) / 2.0
        mid_x = (np.max(x) + np.min(x)) / 2.0
        mid_y = (np.max(y) + np.min(y)) / 2.0
        mid_z = (np.max(z_grid) + np.min(z_grid)) / 2.0
        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        plt.title(f"Lamp Design: {', '.join(parameters['emotions'])}")
        ax.set_axis_off()
        
        # Save figure if output path is provided
        if output_path:
            plt.savefig(output_path)
            print(f"Saved 3D visualization to {output_path}")
        
        plt.close()
    
    def generate_gh_params(self, parameters, output_path=None):
        """Generate parameter file for Grasshopper."""
        # Format for Grasshopper JSON input (simplified for this example)
        gh_params = {
            "schema": "1.0",
            "metadata": {
                "type": "LampParameters",
                "time": parameters["time"],
                "emotions": parameters["emotions"]
            },
            "parameters": {
                "radius": parameters["radius"],
                "height": parameters["height"],
                "thickness": parameters["thickness"],
                "subdivisions": parameters["subdivisions"],
                "layers": parameters["layers"],
                "displacement_scale": parameters["displacement_scale"],
                "smoothing": parameters["smoothing"],
                "displacement_values": parameters["displacement_values"]
            }
        }
        
        # Save to file if output path is provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(gh_params, f, indent=2)
            print(f"Saved Grasshopper parameters to {output_path}")
        
        return gh_params
    
    def process_time_points(self, time_indices=None, visualize=True):
        """Process multiple time points and generate parameters for each."""
        if self.animation_data is None:
            raise ValueError("Animation data not loaded.")
        
        # If no time indices are provided, process all
        if time_indices is None:
            time_indices = range(len(self.animation_data))
        
        results = []
        
        for i in tqdm(time_indices, desc="Generating lamp designs"):
            # Generate parameters
            parameters = self.generate_lamp_parameters(i)
            
            # Generate parameter filename
            time_value = parameters["time"]
            emotions = "_".join(parameters["emotions"])
            param_filename = f"lamp_params_t{float(time_value):.1f}_{emotions}.json"
            
            # Save parameters
            param_path = os.path.join(self.output_dir, param_filename)
            self.generate_gh_params(parameters, param_path)
            
            # Visualize if requested
            if visualize:
                viz_filename = f"lamp_preview_t{float(time_value):.1f}_{emotions}.png"
                viz_path = os.path.join(self.output_dir, viz_filename)
                self.visualize_lamp_3d(parameters, viz_path)
            
            # Add to results
            results.append({
                "time": time_value,
                "emotions": parameters["emotions"],
                "parameters_path": param_path
            })
        
        # Save results to JSON
        results_path = os.path.join(self.output_dir, "lamp_design_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Processed {len(results)} lamp designs. Results saved to {results_path}")
        
        return results
    
    def generate_rhino_python_script(self, parameters_path, output_path=None):
        """Generate a Python script for Rhino to create the lamp model."""
        # Template for Rhino Python script
        script_template = '''
import rhinoscriptsyntax as rs
import Rhino
import json
import math
import os

# Load parameters
with open(r"{parameters_path}", "r") as f:
    data = json.load(f)

params = data["parameters"]
radius = params["radius"]
height = params["height"]
thickness = params["thickness"]
subdivisions = params["subdivisions"]
layers = params["layers"]
displacement_scale = params["displacement_scale"]
smoothing = params["smoothing"]
displacement_values = params["displacement_values"]

# Create lamp shape
def create_lamp():
    # Create points for the outer surface
    points = []
    for i in range(layers):
        z = i * height / (layers - 1)
        layer_points = []
        for j in range(subdivisions):
            angle = j * 2 * math.pi / subdivisions
            displacement = displacement_values[j][i] * displacement_scale
            r = radius + displacement
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            layer_points.append([x, y, z])
        points.append(layer_points)
    
    # Create NURBS surface
    surface = rs.AddNurbsSurface(points)
    
    # Create inner surface (offset)
    inner_surface = rs.OffsetSurface(surface, -thickness)
    
    # Create top and bottom caps
    top_curve = rs.DuplicateSurfaceBorder(surface, 2)[0]
    bottom_curve = rs.DuplicateSurfaceBorder(surface, 3)[0]
    top_surface = rs.AddPlanarSrf(top_curve)
    bottom_surface = rs.AddPlanarSrf(bottom_curve)
    
    # Join all surfaces to create solid
    lamp_solid = rs.JoinSurfaces([surface, inner_surface, top_surface, bottom_surface], True)
    
    return lamp_solid

# Create lamp and set current layer
lamp = create_lamp()
rs.ObjectLayer(lamp, "Lamp")

# Save the file
rs.Command("_Save " + r"{output_3dm}")
print("Lamp model created and saved to {output_3dm}")
'''
        
        # Default output path if not provided
        if output_path is None:
            script_dir = os.path.dirname(parameters_path)
            filename = os.path.basename(parameters_path).replace(".json", ".py")
            output_path = os.path.join(script_dir, filename)
        
        # Create 3dm output path
        output_3dm = output_path.replace(".py", ".3dm")
        
        # Fill in template
        script = script_template.format(
            parameters_path=parameters_path,
            output_3dm=output_3dm
        )
        
        # Save script
        with open(output_path, 'w') as f:
            f.write(script)
        
        print(f"Generated Rhino Python script: {output_path}")
        print(f"Will save 3DM file to: {output_3dm}")
        
        return output_path

# Function to run the generator from command line
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate parametric lamp design")
    parser.add_argument("--data", type=str, required=True, help="Path to animation data JSON")
    parser.add_argument("--output_dir", type=str, default="results/parametric_design", help="Output directory")
    parser.add_argument("--time_index", type=int, help="Specific time index to process")
    parser.add_argument("--no_visualize", action="store_true", help="Skip 3D visualization")
    args = parser.parse_args()
    
    generator = ParametricDesignGenerator(args.data, args.output_dir)
    
    if args.time_index is not None:
        # Process single time point
        parameters = generator.generate_lamp_parameters(args.time_index)
        
        # Generate parameter filename
        time_value = parameters["time"]
        emotions = "_".join(parameters["emotions"])
        param_filename = f"lamp_params_t{float(time_value):.1f}_{emotions}.json"
        param_path = os.path.join(args.output_dir, param_filename)
        
        # Save parameters
        generator.generate_gh_params(parameters, param_path)
        
        # Generate Rhino script
        script_path = param_path.replace(".json", "_rhino.py")
        generator.generate_rhino_python_script(param_path, script_path)
        
        # Visualize unless disabled
        if not args.no_visualize:
            viz_filename = f"lamp_preview_t{float(time_value):.1f}_{emotions}.png"
            viz_path = os.path.join(args.output_dir, viz_filename)
            generator.visualize_lamp_3d(parameters, viz_path)
    else:
        # Process all time points
        results = generator.process_time_points(visualize=not args.no_visualize)
        
        # Generate Rhino script for the first result (as an example)
        if results:
            param_path = results[0]["parameters_path"]
            script_path = param_path.replace(".json", "_rhino.py")
            generator.generate_rhino_python_script(param_path, script_path)

if __name__ == "__main__":
    main() 