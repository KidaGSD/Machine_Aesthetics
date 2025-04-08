import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import cv2
from pathlib import Path
from matplotlib.gridspec import GridSpec

class ResultEvaluator:
    """Evaluates and visualizes the audio-texture-parametric pipeline results."""
    
    def __init__(self, 
                 audio_timeline_path=None,
                 texture_timeline_path=None, 
                 blended_textures_dir=None,
                 parametric_design_dir=None):
        """Initialize with paths to result files."""
        self.audio_timeline = None
        self.texture_timeline = None
        self.blended_textures = []
        self.displacement_maps = []
        self.parametric_designs = []
        
        # Load data if paths provided
        if audio_timeline_path and os.path.exists(audio_timeline_path):
            self.load_audio_timeline(audio_timeline_path)
        
        if texture_timeline_path and os.path.exists(texture_timeline_path):
            self.load_texture_timeline(texture_timeline_path)
        
        if blended_textures_dir and os.path.exists(blended_textures_dir):
            self.load_blended_textures(blended_textures_dir)
        
        if parametric_design_dir and os.path.exists(parametric_design_dir):
            self.load_parametric_designs(parametric_design_dir)
    
    def load_audio_timeline(self, path):
        """Load audio emotion timeline from CSV."""
        try:
            self.audio_timeline = pd.read_csv(path)
            print(f"Loaded audio timeline with {len(self.audio_timeline)} time points")
            return True
        except Exception as e:
            print(f"Error loading audio timeline: {e}")
            return False
    
    def load_texture_timeline(self, path):
        """Load texture timeline from JSON."""
        try:
            with open(path, 'r') as f:
                self.texture_timeline = json.load(f)
            print(f"Loaded texture timeline with {len(self.texture_timeline)} time points")
            return True
        except Exception as e:
            print(f"Error loading texture timeline: {e}")
            return False
    
    def load_blended_textures(self, directory):
        """Load blended textures and displacement maps."""
        # Load textures
        texture_dir = os.path.join(directory, "textures")
        if os.path.exists(texture_dir):
            texture_files = [os.path.join(texture_dir, f) for f in os.listdir(texture_dir) 
                            if f.endswith('.png') or f.endswith('.jpg')]
            texture_files.sort()
            self.blended_textures = texture_files
            print(f"Found {len(self.blended_textures)} blended textures")
        
        # Load displacement maps
        disp_dir = os.path.join(directory, "displacement_maps")
        if os.path.exists(disp_dir):
            disp_files = [os.path.join(disp_dir, f) for f in os.listdir(disp_dir) 
                         if f.endswith('.png') or f.endswith('.jpg')]
            disp_files.sort()
            self.displacement_maps = disp_files
            print(f"Found {len(self.displacement_maps)} displacement maps")
        
        return len(self.blended_textures) > 0 or len(self.displacement_maps) > 0
    
    def load_parametric_designs(self, directory):
        """Load parametric design files."""
        try:
            param_files = [os.path.join(directory, f) for f in os.listdir(directory) 
                          if f.endswith('.json') and "lamp_params" in f]
            param_files.sort()
            self.parametric_designs = param_files
            print(f"Found {len(self.parametric_designs)} parametric design files")
            return True
        except Exception as e:
            print(f"Error loading parametric designs: {e}")
            return False
    
    def evaluate_audio_timeline(self):
        """Evaluate the audio timeline quality."""
        if self.audio_timeline is None:
            print("No audio timeline loaded")
            return {}
        
        # Calculate basic statistics
        stats = {
            "num_points": len(self.audio_timeline),
            "valence_mean": self.audio_timeline["Valence"].mean(),
            "valence_std": self.audio_timeline["Valence"].std(),
            "arousal_mean": self.audio_timeline["Arousal"].mean(),
            "arousal_std": self.audio_timeline["Arousal"].std(),
            "valence_range": (self.audio_timeline["Valence"].min(), self.audio_timeline["Valence"].max()),
            "arousal_range": (self.audio_timeline["Arousal"].min(), self.audio_timeline["Arousal"].max()),
        }
        
        # Evaluate quality based on variance and range
        evaluation = {
            "emotional_variance": "Low" if stats["valence_std"] < 0.1 and stats["arousal_std"] < 0.1 else 
                               "Medium" if stats["valence_std"] < 0.2 and stats["arousal_std"] < 0.2 else 
                               "High",
            "emotional_range": "Limited" if (stats["valence_range"][1] - stats["valence_range"][0] < 0.3 or
                                         stats["arousal_range"][1] - stats["arousal_range"][0] < 0.3) else 
                             "Good" if (stats["valence_range"][1] - stats["valence_range"][0] < 0.6 or
                                     stats["arousal_range"][1] - stats["arousal_range"][0] < 0.6) else 
                             "Excellent",
            "temporal_resolution": "Low" if stats["num_points"] < 10 else 
                                 "Medium" if stats["num_points"] < 30 else 
                                 "High"
        }
        
        return {"stats": stats, "evaluation": evaluation}
    
    def evaluate_texture_fusion(self, sample_size=5):
        """Evaluate texture fusion quality."""
        if not self.blended_textures or not self.displacement_maps:
            print("No blended textures or displacement maps loaded")
            return {}
        
        results = []
        
        # Select a sample of textures to evaluate
        sample_indices = np.linspace(0, len(self.blended_textures)-1, sample_size, dtype=int)
        
        for i in sample_indices:
            if i < len(self.blended_textures) and i < len(self.displacement_maps):
                texture_path = self.blended_textures[i]
                disp_path = self.displacement_maps[i]
                
                # Load images
                texture = cv2.imread(texture_path, cv2.IMREAD_GRAYSCALE)
                disp_map = cv2.imread(disp_path, cv2.IMREAD_GRAYSCALE)
                
                if texture is None or disp_map is None:
                    continue
                
                # Calculate metrics
                texture_contrast = cv2.mean(texture)[0] / 255
                texture_variance = np.var(texture) / (255 * 255)
                
                disp_contrast = cv2.mean(disp_map)[0] / 255
                disp_variance = np.var(disp_map) / (255 * 255)
                
                # Edge detection to evaluate detail
                texture_edges = cv2.Canny(texture, 100, 200)
                disp_edges = cv2.Canny(disp_map, 100, 200)
                
                texture_edge_density = np.count_nonzero(texture_edges) / (texture_edges.shape[0] * texture_edges.shape[1])
                disp_edge_density = np.count_nonzero(disp_edges) / (disp_edges.shape[0] * disp_edges.shape[1])
                
                results.append({
                    "texture_path": texture_path,
                    "disp_path": disp_path,
                    "texture_contrast": texture_contrast,
                    "texture_variance": texture_variance,
                    "texture_edge_density": texture_edge_density,
                    "disp_contrast": disp_contrast,
                    "disp_variance": disp_variance,
                    "disp_edge_density": disp_edge_density,
                    "quality_score": (texture_variance + disp_variance + texture_edge_density + disp_edge_density) / 4
                })
        
        # Overall evaluation
        avg_quality = np.mean([r["quality_score"] for r in results]) if results else 0
        
        evaluation = {
            "texture_clarity": "Low" if avg_quality < 0.1 else "Medium" if avg_quality < 0.2 else "High",
            "detail_preservation": "Poor" if np.mean([r["texture_edge_density"] for r in results]) < 0.05 else
                                 "Fair" if np.mean([r["texture_edge_density"] for r in results]) < 0.1 else
                                 "Good",
            "displacement_contrast": "Low" if np.mean([r["disp_contrast"] for r in results]) < 0.4 else
                                   "Medium" if np.mean([r["disp_contrast"] for r in results]) < 0.6 else
                                   "High"
        }
        
        return {"detailed_results": results, "evaluation": evaluation}
    
    def visualize_results(self, output_dir="evaluation_results"):
        """Create visualizations for results evaluation."""
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Visualize audio timeline
        if self.audio_timeline is not None:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(self.audio_timeline["Start Time (s)"], self.audio_timeline["Valence"], 'b-', label='Valence')
            ax.plot(self.audio_timeline["Start Time (s)"], self.audio_timeline["Arousal"], 'r-', label='Arousal')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Value')
            ax.set_title('Audio Emotion Timeline')
            ax.legend()
            ax.grid(True)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "audio_timeline_evaluation.png"))
            plt.close()
        
        # 2. Visualize texture timeline with selected textures
        if self.texture_timeline is not None and len(self.texture_timeline) > 0:
            # Create a figure showing emotions over time with example textures
            sample_indices = np.linspace(0, len(self.texture_timeline)-1, 5, dtype=int)
            fig = plt.figure(figsize=(15, 10))
            gs = GridSpec(2, 5, height_ratios=[1, 2])
            
            # Plot emotions over time
            ax_timeline = fig.add_subplot(gs[0, :])
            times = [entry["time"] for entry in self.texture_timeline]
            valences = [entry["valence"] for entry in self.texture_timeline]
            arousals = [entry["arousal"] for entry in self.texture_timeline]
            
            ax_timeline.plot(times, valences, 'b-', label='Valence')
            ax_timeline.plot(times, arousals, 'r-', label='Arousal')
            ax_timeline.set_xlabel('Time (s)')
            ax_timeline.set_ylabel('Value')
            ax_timeline.set_title('Emotion Timeline with Selected Textures')
            ax_timeline.legend()
            ax_timeline.grid(True)
            
            # Plot sample textures
            for i, idx in enumerate(sample_indices):
                if idx < len(self.texture_timeline):
                    entry = self.texture_timeline[idx]
                    
                    ax_text = fig.add_subplot(gs[1, i])
                    ax_text.axis('off')
                    
                    # Try to load and display a texture from this time point
                    if "textures" in entry and len(entry["textures"]) > 0:
                        texture_path = entry["textures"][0]["texture_path"]
                        if os.path.exists(texture_path):
                            try:
                                img = plt.imread(texture_path)
                                ax_text.imshow(img)
                                
                                # Mark sample points on timeline
                                ax_timeline.plot(entry["time"], entry["valence"], 'bo', markersize=8)
                                ax_timeline.plot(entry["time"], entry["arousal"], 'ro', markersize=8)
                                
                                # Add time and emotion label
                                emotions_str = ", ".join(entry["emotions"])
                                ax_text.set_title(f"t={entry['time']:.1f}s\n{emotions_str}", fontsize=10)
                            except:
                                ax_text.text(0.5, 0.5, "Image Error", ha='center', va='center')
                        else:
                            ax_text.text(0.5, 0.5, "Missing Image", ha='center', va='center')
                    else:
                        ax_text.text(0.5, 0.5, "No Texture", ha='center', va='center')
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "texture_timeline_evaluation.png"))
            plt.close()
        
        # 3. Visualize texture fusion quality
        if self.blended_textures and self.displacement_maps:
            # Select samples
            sample_size = min(5, len(self.blended_textures), len(self.displacement_maps))
            sample_indices = np.linspace(0, len(self.blended_textures)-1, sample_size, dtype=int)
            
            fig, axes = plt.subplots(sample_size, 2, figsize=(12, 3*sample_size))
            if sample_size == 1:
                axes = axes.reshape(1, 2)
                
            for i, idx in enumerate(sample_indices):
                if idx < len(self.blended_textures) and idx < len(self.displacement_maps):
                    texture_path = self.blended_textures[idx]
                    disp_path = self.displacement_maps[idx]
                    
                    # Load images
                    texture = cv2.imread(texture_path, cv2.IMREAD_GRAYSCALE)
                    disp_map = cv2.imread(disp_path, cv2.IMREAD_GRAYSCALE)
                    
                    if texture is not None:
                        axes[i, 0].imshow(texture, cmap='gray')
                        axes[i, 0].set_title(f"Texture {idx}", fontsize=10)
                        axes[i, 0].axis('off')
                    else:
                        axes[i, 0].text(0.5, 0.5, "Image Error", ha='center', va='center')
                        axes[i, 0].axis('off')
                    
                    if disp_map is not None:
                        # Apply a colormap to displacement for better visualization
                        disp_colored = cv2.applyColorMap(disp_map, cv2.COLORMAP_JET)
                        disp_colored = cv2.cvtColor(disp_colored, cv2.COLOR_BGR2RGB)
                        axes[i, 1].imshow(disp_colored)
                        axes[i, 1].set_title(f"Displacement {idx}", fontsize=10)
                        axes[i, 1].axis('off')
                    else:
                        axes[i, 1].text(0.5, 0.5, "Image Error", ha='center', va='center')
                        axes[i, 1].axis('off')
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "texture_fusion_evaluation.png"))
            plt.close()
        
        # 4. Compare original vs blended textures (if we can find originals)
        if self.texture_timeline is not None and len(self.texture_timeline) > 0 and self.blended_textures:
            # Try to find matching original textures and blended textures
            orig_textures = []
            for entry in self.texture_timeline:
                if "textures" in entry and len(entry["textures"]) > 0:
                    texture_path = entry["textures"][0]["texture_path"]
                    if os.path.exists(texture_path):
                        orig_textures.append(texture_path)
            
            if orig_textures:
                sample_size = min(5, len(orig_textures), len(self.blended_textures))
                if sample_size > 0:
                    fig, axes = plt.subplots(sample_size, 2, figsize=(12, 3*sample_size))
                    if sample_size == 1:
                        axes = axes.reshape(1, 2)
                    
                    for i in range(sample_size):
                        orig_idx = min(i, len(orig_textures)-1)
                        blend_idx = min(i, len(self.blended_textures)-1)
                        
                        orig_path = orig_textures[orig_idx]
                        blend_path = self.blended_textures[blend_idx]
                        
                        try:
                            orig_img = plt.imread(orig_path)
                            axes[i, 0].imshow(orig_img)
                            axes[i, 0].set_title(f"Original Texture", fontsize=10)
                            axes[i, 0].axis('off')
                        except:
                            axes[i, 0].text(0.5, 0.5, "Image Error", ha='center', va='center')
                            axes[i, 0].axis('off')
                        
                        try:
                            blend_img = plt.imread(blend_path)
                            axes[i, 1].imshow(blend_img, cmap='gray')
                            axes[i, 1].set_title(f"Blended Texture", fontsize=10)
                            axes[i, 1].axis('off')
                        except:
                            axes[i, 1].text(0.5, 0.5, "Image Error", ha='center', va='center')
                            axes[i, 1].axis('off')
                    
                    plt.tight_layout()
                    plt.savefig(os.path.join(output_dir, "original_vs_blended_comparison.png"))
                    plt.close()
        
        # 5. Generate a summary report
        with open(os.path.join(output_dir, "evaluation_summary.txt"), 'w') as f:
            f.write("# Audio-Texture-Parametric Pipeline Evaluation\n\n")
            
            # Audio evaluation
            audio_eval = self.evaluate_audio_timeline()
            f.write("## Audio Timeline Evaluation\n")
            if audio_eval:
                f.write(f"- Number of time points: {audio_eval['stats']['num_points']}\n")
                f.write(f"- Emotional variance: {audio_eval['evaluation']['emotional_variance']}\n")
                f.write(f"- Emotional range: {audio_eval['evaluation']['emotional_range']}\n")
                f.write(f"- Temporal resolution: {audio_eval['evaluation']['temporal_resolution']}\n\n")
            else:
                f.write("- No audio timeline data available\n\n")
            
            # Texture fusion evaluation
            texture_eval = self.evaluate_texture_fusion()
            f.write("## Texture Fusion Evaluation\n")
            if texture_eval and "evaluation" in texture_eval:
                f.write(f"- Texture clarity: {texture_eval['evaluation']['texture_clarity']}\n")
                f.write(f"- Detail preservation: {texture_eval['evaluation']['detail_preservation']}\n")
                f.write(f"- Displacement contrast: {texture_eval['evaluation']['displacement_contrast']}\n\n")
            else:
                f.write("- No texture fusion data available\n\n")
            
            # Recommendations
            f.write("## Recommendations\n")
            
            # Audio recommendations
            if audio_eval and "evaluation" in audio_eval:
                if audio_eval['evaluation']['emotional_variance'] == "Low":
                    f.write("- Increase emotional variance in audio by using more expressive content\n")
                if audio_eval['evaluation']['emotional_range'] == "Limited":
                    f.write("- Expand emotional range in audio by including more diverse emotional content\n")
                if audio_eval['evaluation']['temporal_resolution'] == "Low":
                    f.write("- Increase temporal resolution by using smaller chunk sizes in audio analysis\n")
            
            # Texture fusion recommendations
            if texture_eval and "evaluation" in texture_eval:
                if texture_eval['evaluation']['texture_clarity'] == "Low":
                    f.write("- Improve texture clarity by adjusting blending weights or using more distinct textures\n")
                if texture_eval['evaluation']['detail_preservation'] == "Poor":
                    f.write("- Enhance detail preservation by reducing blur in displacement maps\n")
                if texture_eval['evaluation']['displacement_contrast'] == "Low":
                    f.write("- Increase displacement contrast by adjusting the scale factor in displacement map generation\n")
            
            f.write("\n## Overall Assessment\n")
            overall_issues = []
            
            if not self.audio_timeline:
                overall_issues.append("- Audio timeline is missing or empty")
            if not self.texture_timeline:
                overall_issues.append("- Texture timeline is missing or empty")
            if not self.blended_textures:
                overall_issues.append("- Blended textures are missing or empty")
            if not self.displacement_maps:
                overall_issues.append("- Displacement maps are missing or empty")
            if not self.parametric_designs:
                overall_issues.append("- Parametric designs are missing or empty")
            
            if overall_issues:
                f.write("Issues found:\n")
                for issue in overall_issues:
                    f.write(f"{issue}\n")
            else:
                f.write("All components of the pipeline are present.\n")
            
            # Specific recommendations for improving quality
            f.write("\n## Specific Improvement Suggestions\n")
            f.write("1. For texture fusion clarity:\n")
            f.write("   - Try increasing contrast in the input textures\n")
            f.write("   - Adjust the blur kernel size for displacement maps (smaller for more detail)\n")
            f.write("   - Experiment with different blending weights\n\n")
            
            f.write("2. For emotion-texture mapping:\n")
            f.write("   - Update emotion mapping ranges in example_emotion_mapping.json\n")
            f.write("   - Run the texture classification with a higher confidence threshold\n")
            f.write("   - Add more emotion labels to expand the palette\n\n")
            
            f.write("3. For parametric design:\n")
            f.write("   - Adjust displacement scaling in the Grasshopper definition\n")
            f.write("   - Experiment with different base geometries\n")
            f.write("   - Fine-tune emotion-to-parameter mappings\n")
        
        print(f"Evaluation results saved to {output_dir}")
        
    def generate_report(self, output_dir="evaluation_results"):
        """Generate a comprehensive evaluation report."""
        # First run visualizations
        self.visualize_results(output_dir)
        
        # Then print a summary to console
        print("\n=== EVALUATION SUMMARY ===")
        
        # Audio evaluation
        audio_eval = self.evaluate_audio_timeline()
        print("\nAudio Timeline Evaluation:")
        if audio_eval and "evaluation" in audio_eval:
            print(f"- Emotional variance: {audio_eval['evaluation']['emotional_variance']}")
            print(f"- Emotional range: {audio_eval['evaluation']['emotional_range']}")
            print(f"- Temporal resolution: {audio_eval['evaluation']['temporal_resolution']}")
        else:
            print("- No audio timeline data available")
        
        # Texture fusion evaluation
        texture_eval = self.evaluate_texture_fusion()
        print("\nTexture Fusion Evaluation:")
        if texture_eval and "evaluation" in texture_eval:
            print(f"- Texture clarity: {texture_eval['evaluation']['texture_clarity']}")
            print(f"- Detail preservation: {texture_eval['evaluation']['detail_preservation']}")
            print(f"- Displacement contrast: {texture_eval['evaluation']['displacement_contrast']}")
        else:
            print("- No texture fusion data available")
        
        # Key recommendations
        print("\nKey Recommendations:")
        if texture_eval and "evaluation" in texture_eval and texture_eval['evaluation']['texture_clarity'] == "Low":
            print("1. Improve texture clarity:")
            print("   - Adjust blending weights")
            print("   - Use more distinct textures")
            print("   - Reduce the number of textures being blended at once")
        
        if audio_eval and "evaluation" in audio_eval and audio_eval['evaluation']['emotional_variance'] == "Low":
            print("2. Increase emotional variance in audio:")
            print("   - Use more expressive audio content")
            print("   - Adjust audio analysis parameters")
        
        print("\nSee the full report in:", os.path.join(output_dir, "evaluation_summary.txt"))
        print("==============================")

# Function to run the evaluator
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Audio-Texture-Parametric Pipeline results")
    parser.add_argument("--audio_timeline", type=str, help="Path to audio timeline CSV")
    parser.add_argument("--texture_timeline", type=str, help="Path to texture timeline JSON")
    parser.add_argument("--blended_dir", type=str, help="Path to blended textures directory")
    parser.add_argument("--design_dir", type=str, help="Path to parametric design directory")
    parser.add_argument("--output_dir", type=str, default="evaluation_results", help="Output directory for evaluation")
    args = parser.parse_args()
    
    # Use default paths if not provided
    if not args.audio_timeline:
        args.audio_timeline = "results/audio_texture/audio_emotion_timeline.csv"
    
    if not args.texture_timeline:
        args.texture_timeline = "results/audio_texture/texture_timeline.json"
    
    if not args.blended_dir:
        args.blended_dir = "results/blended_textures"
    
    if not args.design_dir:
        args.design_dir = "results/parametric_design"
    
    evaluator = ResultEvaluator(
        audio_timeline_path=args.audio_timeline,
        texture_timeline_path=args.texture_timeline,
        blended_textures_dir=args.blended_dir,
        parametric_design_dir=args.design_dir
    )
    
    evaluator.generate_report(args.output_dir)

if __name__ == "__main__":
    main()