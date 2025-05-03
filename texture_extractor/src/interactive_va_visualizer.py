import os
import sys
import pandas as pd
import pandas as pd
import numpy as np
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image # Uncommented PIL
import base64       # Uncommented base64
from io import BytesIO  # Uncommented BytesIO
import argparse
from pathlib import Path
import glob
# import matplotlib.pyplot as plt # Remove Matplotlib (or keep if needed for other plots)
# import matplotlib.colors as mcolors # Remove Matplotlib

# Add the src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import from binary_va_classifier - keep this if needed for data
try:
    from binary_va_classifier import BINARY_VA_DESCRIPTORS, QUADRANT_DESCRIPTORS
except ImportError:
    print("Warning: Could not import descriptors from binary_va_classifier. Quadrant info might be unavailable.")
    BINARY_VA_DESCRIPTORS = {}
    QUADRANT_DESCRIPTORS = {}

# --- Helper Functions ---
def encode_image_as_base64(image_path, size=(64, 64)):
    """Reads an image, resizes it, encodes it as Base64, and returns a data URI."""
    try:
        # Directly use the image_path assuming it's absolute or correctly relative from the CSV's perspective
        img_path = Path(image_path) 
        if not img_path.exists():
            print(f"Warning: Image file not found at {img_path}")
            return None

        img = Image.open(img_path).convert("RGB") # Convert to RGB for consistency
        img.thumbnail(size) # Resize to thumbnail
        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True) # Use PNG for better quality
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_str
    except FileNotFoundError:
        print(f"Warning: Image file not found at {image_path}")
        return None
    except Exception as e:
        print(f"Warning: Could not encode image {image_path}: {e}")
        return None

def load_classification_results(results_path):
    """Load classification results from CSV file."""
    try:
        df = pd.read_csv(results_path)
        # Ensure necessary columns exist for plotting and hover
        required_cols = ['image_path', 'valence_normalized', 'arousal_normalized',
                         'valence_score', 'arousal_score', 'category', 'quadrant']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
             # Try to derive missing normalized columns if scores exist
             if 'valence_normalized' not in df.columns and 'valence_score' in df.columns:
                 print("Deriving 'valence_normalized' from 'valence_score'.")
                 # Simple normalization (adjust if a specific range is needed)
                 df['valence_normalized'] = (df['valence_score'] - df['valence_score'].mean()) / df['valence_score'].std()
                 missing.remove('valence_normalized')
             if 'arousal_normalized' not in df.columns and 'arousal_score' in df.columns:
                 print("Deriving 'arousal_normalized' from 'arousal_score'.")
                 df['arousal_normalized'] = (df['arousal_score'] - df['arousal_score'].mean()) / df['arousal_score'].std()
                 missing.remove('arousal_normalized')

             # If still missing critical columns, raise error
             if any(col in missing for col in ['image_path', 'valence_normalized', 'arousal_normalized', 'valence_score', 'arousal_score', 'category']):
                 print(f"Error: Missing required columns in CSV: {missing}")
                 return None

        # Ensure paths are strings and handle potential NaN values
        df['image_path'] = df['image_path'].astype(str)
        df.dropna(subset=['valence_normalized', 'arousal_normalized'], inplace=True) # Drop rows where plot coords are missing

        print(f"Loaded {len(df)} texture classification results from {results_path}")
        return df
    except FileNotFoundError:
        print(f"Error: Results file not found at {results_path}")
        return None
    except Exception as e:
        print(f"Error loading or processing results from {results_path}: {e}")
        return None

def create_interactive_visualization(results_df, output_html_path):
    """Create an interactive scatter plot visualization using Plotly."""
    if results_df is None or results_df.empty:
        print("Error: No data provided for interactive visualization.")
        return False

    try:
        # --- Add Image Encoding Step ---
        print("Encoding images for hover...")
        # Make sure image paths are accessible. Adjust if paths in CSV are relative differently.
        total_images = len(results_df)
        
        # Generate simpler base64 strings without data URI prefix
        results_df['img_base64'] = results_df['image_path'].apply(lambda path: encode_image_as_base64(path, (64, 64)))
        print(f"Image encoding complete. Encoded {total_images} images.")
        
        # Filter out rows where image encoding failed
        original_count = len(results_df)
        results_df = results_df.dropna(subset=['img_base64'])
        if len(results_df) < original_count:
            print(f"Warning: Dropped {original_count - len(results_df)} rows due to image encoding errors.")
        
        # Sample check
        if not results_df.empty:
            print(f"Sample base64 length: {len(results_df['img_base64'].iloc[0])}")
        
        if results_df.empty:
            print("Error: No valid image data could be encoded. Cannot create plot.")
            return False
        # --- End Image Encoding Step ---

        # Create the scatter plot
        fig = px.scatter(
            results_df,
            x='valence_normalized',
            y='arousal_normalized',
            color='category',  # Color by texture category
            title="Interactive Valence-Arousal Texture Visualization",
            labels={
                'valence_normalized': "Valence (Negative ← → Positive)",
                'arousal_normalized': "Arousal (Calm ← → Energetic)",
                'category': "Texture Category"
            },
            # Use custom data for tooltip
            custom_data=['image_path', 'category', 'valence_score', 'arousal_score', 'quadrant', 'img_base64', 'filename'],
        )

        # Define hover template with base64 image
        hover_template = """
        <img src='data:image/png;base64,%{customdata[5]}' width=64 height=64><br>
        <b>File:</b> %{customdata[6]}<br>
        <b>Category:</b> %{customdata[1]}<br>
        <b>Valence:</b> %{x:.3f}<br>
        <b>Arousal:</b> %{y:.3f}<br>
        <b>Quadrant:</b> %{customdata[4]}<br>
        <extra></extra>
        """
        
        fig.update_traces(
            hovertemplate=hover_template,
            marker=dict(size=8),
        )

        # Add quadrant lines
        fig.add_shape(type="line", x0=-1.1, y0=0, x1=1.1, y1=0, line=dict(color="Black", width=1, dash="dash"))
        fig.add_shape(type="line", x0=0, y0=-1.1, x1=0, y1=1.1, line=dict(color="Black", width=1, dash="dash"))

        # Set axis limits and ensure aspect ratio is equal
        axis_range = max(results_df['valence_normalized'].abs().max(), results_df['arousal_normalized'].abs().max()) * 1.1
        axis_range = max(axis_range, 1.1) # Ensure at least -1.1 to 1.1 range
        fig.update_xaxes(range=[-axis_range, axis_range], zeroline=False)
        fig.update_yaxes(range=[-axis_range, axis_range], zeroline=False, scaleanchor="x", scaleratio=1)

        fig.update_layout(
            xaxis_title="Valence (Negative → Positive)",
            yaxis_title="Arousal (Calm → Energetic)",
            legend_title_text='Texture Category',
            hovermode='closest', # Ensure hover works well
            width=900, # Adjust width
            height=800, # Adjust height
            hoverlabel=dict(
                bgcolor="white",
                font_size=12,
                font_family="Arial"
            )
        )

        # Save the figure as an HTML file
        print(f"Generating HTML visualization at: {output_html_path}")
        fig.write_html(
            output_html_path,
            include_plotlyjs=True,
            full_html=True,
            config={'responsive': True}
        )
        print(f"Interactive visualization saved to: {output_html_path}")
        return True

    except Exception as e:
        print(f"Error creating interactive visualization: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_latest_results(results_dir):
    """Find the latest combined results file in the given directory."""
    # Prioritize the specific combined file
    search_pattern_all = os.path.join(results_dir, "va_classification_all.csv")
    matching_files_all = glob.glob(search_pattern_all)
    
    if matching_files_all:
        print(f"Found specific combined file: {matching_files_all[0]}")
        return matching_files_all[0]
    
    # If not found, search recursively for any va_classification.csv
    print(f"Combined file not found at {search_pattern_all}, searching recursively...")
    search_pattern_any = os.path.join(results_dir, "**", "va_classification.csv")
    matching_files_any = glob.glob(search_pattern_any, recursive=True)
    
    if matching_files_any:
        # Sort by modification time, newest first
        matching_files_any.sort(key=os.path.getmtime, reverse=True)
        print(f"Found latest result file: {matching_files_any[0]}")
        return matching_files_any[0]
    
    print(f"No result files found matching patterns in {results_dir}")
    return None

def parse_args():
    # Update parser description and arguments for interactive HTML output
    parser = argparse.ArgumentParser(description="Interactive VA Texture Visualization using Plotly")
    parser.add_argument("--results",
                      help="Path to VA classification results CSV file. If not provided, will try to find the latest 'va_classification_all.csv' or 'va_classification.csv' in --results-dir.")
    parser.add_argument("--results-dir", default="texture_extractor/data/binary_va_classification", # Adjusted default path
                      help="Directory containing VA classification results (used if --results not provided)")
    # Update output argument help text and default value for HTML
    parser.add_argument("--output", default="results/va_interactive_visualization.html",
                      help="Output HTML file path for the interactive visualization (e.g., .html)")
    # base-path might be useful if linking images instead of embedding
    # parser.add_argument("--base-path", default=os.getcwd(), help="Base path for resolving relative image paths if needed.")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Determine results file to use
    results_file = args.results
    if not results_file:
        print(f"No results file specified, searching in {args.results_dir}...")
        # Use Path for better path handling
        results_dir_path = Path(args.results_dir)
        print(f"No results file specified, searching in {results_dir_path}...")
        results_file = find_latest_results(str(results_dir_path)) # find_latest_results expects string

        if not results_file:
            print(f"Error: Could not find VA classification results in {results_dir_path}")
            print("Please specify a results file with --results or ensure 'va_classification_all.csv' or 'va_classification.csv' exists in the specified directory.")
            sys.exit(1)

    print(f"Using classification results from: {results_file}")

    # Load the results
    results_df = load_classification_results(results_file)
    if results_df is None:
        print("Error loading or processing classification results. Exiting.")
        sys.exit(1)

    # Add filename column if missing (useful for hover)
    if 'filename' not in results_df.columns and 'image_path' in results_df.columns:
        results_df['filename'] = results_df['image_path'].apply(lambda p: Path(p).name)
    
    # Ensure image paths are absolute
    if 'image_path' in results_df.columns:
        # If relative paths are used, make them absolute relative to the CSV location
        results_dir = os.path.dirname(os.path.abspath(results_file))
        def ensure_absolute_path(path):
            if os.path.isabs(path):
                return path
            return os.path.abspath(os.path.join(results_dir, path))
        
        # Apply the conversion
        results_df['image_path'] = results_df['image_path'].apply(ensure_absolute_path)
        print(f"Ensured absolute paths for {len(results_df)} images")

    # Create output directory if needed
    output_path = Path(args.output)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True) # Use Pathlib's mkdir

    # Create the interactive visualization
    success = create_interactive_visualization(
        results_df,
        str(output_path) # Plotly expects string path
    )

    if success:
        print(f"Interactive plot created successfully!")
        print(f"HTML file saved at: {output_path.resolve()}") # Use resolve for absolute path
    else:
        print("Failed to create interactive plot.")
        sys.exit(1)

    sys.exit(0)
