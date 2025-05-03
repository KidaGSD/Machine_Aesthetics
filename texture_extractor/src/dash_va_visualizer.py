import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from PIL import Image
import base64
from io import BytesIO
from pathlib import Path
import os
import sys
import glob
import argparse

# --- Helper Functions ---

def encode_image_as_base64(image_path, size=(128, 128)): # Slightly larger default size
    """Reads an image, resizes it, encodes it as Base64, and returns a data URI."""
    placeholder_uri = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" # 1x1 transparent GIF
    try:
        img_path = Path(image_path)
        # --- DEBUG PRINT ADDED ---
        print(f"Checking path: {img_path} | Exists: {img_path.exists()}") 
        # --- END DEBUG PRINT ---
        if not img_path.exists():
            # This print statement might be redundant now with the one above, but keep for clarity
            print(f"Warning: Image file not found at {img_path}") 
            return placeholder_uri

        img = Image.open(img_path).convert("RGB")
        img.thumbnail(size)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        uri = f"data:image/png;base64,{encoded}"
        return uri
    except FileNotFoundError:
        # This might be less likely to trigger if exists() check works, but keep as fallback
        print(f"Warning: FileNotFoundError for {image_path}") 
        return placeholder_uri
    except Exception as e:
        print(f"Warning: Could not encode image {image_path}: {e}")
        return placeholder_uri

def load_classification_results(results_path):
    """Load classification results from CSV file."""
    try:
        df = pd.read_csv(results_path)
        required_cols = ['image_path', 'valence_normalized', 'arousal_normalized',
                         'valence_score', 'arousal_score', 'category', 'quadrant']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
             if 'valence_normalized' not in df.columns and 'valence_score' in df.columns:
                 print("Deriving 'valence_normalized' from 'valence_score'.")
                 df['valence_normalized'] = (df['valence_score'] - df['valence_score'].mean()) / df['valence_score'].std()
                 missing.remove('valence_normalized')
             if 'arousal_normalized' not in df.columns and 'arousal_score' in df.columns:
                 print("Deriving 'arousal_normalized' from 'arousal_score'.")
                 df['arousal_normalized'] = (df['arousal_score'] - df['arousal_score'].mean()) / df['arousal_score'].std()
                 missing.remove('arousal_normalized')

             if any(col in missing for col in ['image_path', 'valence_normalized', 'arousal_normalized', 'valence_score', 'arousal_score', 'category']):
                 print(f"Error: Missing required columns in CSV: {missing}")
                 return None

        df['image_path'] = df['image_path'].astype(str)
        df.dropna(subset=['valence_normalized', 'arousal_normalized'], inplace=True)

        # Add filename column if missing
        if 'filename' not in df.columns and 'image_path' in df.columns:
            df['filename'] = df['image_path'].apply(lambda p: Path(p).name)

        print(f"Loaded {len(df)} texture classification results from {results_path}")
        return df
    except FileNotFoundError:
        print(f"Error: Results file not found at {results_path}")
        return None
    except Exception as e:
        print(f"Error loading or processing results from {results_path}: {e}")
        return None

def find_latest_results(results_dir):
    """Find the latest combined results file in the given directory."""
    search_pattern_all = os.path.join(results_dir, "va_classification_all.csv")
    matching_files_all = glob.glob(search_pattern_all)
    if matching_files_all: return matching_files_all[0]
    print(f"Combined file not found at {search_pattern_all}, searching recursively...")
    search_pattern_any = os.path.join(results_dir, "**", "va_classification.csv")
    matching_files_any = glob.glob(search_pattern_any, recursive=True)
    if matching_files_any:
        matching_files_any.sort(key=os.path.getmtime, reverse=True)
        return matching_files_any[0]
    return None

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Dash VA Texture Visualization with Hover Images")
parser.add_argument("--results", help="Path to VA classification results CSV file.")
parser.add_argument("--results-dir", default="texture_extractor/data/binary_va_classification",
                    help="Directory containing VA classification results (used if --results not provided)")
parser.add_argument("--port", type=int, default=8050, help="Port for the Dash server")
args = parser.parse_args()

# --- Load Data ---
results_file = args.results
if not results_file:
    print(f"No results file specified, searching in {args.results_dir}...")
    results_file = find_latest_results(args.results_dir)
    if not results_file:
        print(f"Error: Could not find VA classification results in {args.results_dir}")
        sys.exit(1)

print(f"Using classification results from: {results_file}")
df = load_classification_results(results_file)
if df is None:
    print("Error loading data. Exiting.")
    sys.exit(1)

# --- Create Plotly Figure ---
fig = px.scatter(
    df,
    x='valence_normalized',
    y='arousal_normalized',
    color='category',
    title="Interactive Valence-Arousal Texture Visualization",
    labels={
        'valence_normalized': "Valence (Negative ← → Positive)",
        'arousal_normalized': "Arousal (Calm ← → Energetic)",
        'category': "Texture Category"
    },
    custom_data=['image_path', 'category', 'valence_score', 'arousal_score', 'quadrant'], # Keep data needed for callback
    hover_name='filename' # Use filename for default hover info if needed
)
fig.update_traces(hoverinfo='none', hovertemplate=None) # Disable default Plotly hover, use Dash callback instead

# Add quadrant lines and adjust layout
fig.add_shape(type="line", x0=-1.1, y0=0, x1=1.1, y1=0, line=dict(color="Black", width=1, dash="dash"))
fig.add_shape(type="line", x0=0, y0=-1.1, x1=0, y1=1.1, line=dict(color="Black", width=1, dash="dash"))
axis_range = max(df['valence_normalized'].abs().max(), df['arousal_normalized'].abs().max()) * 1.1
axis_range = max(axis_range, 1.1)
fig.update_xaxes(range=[-axis_range, axis_range], zeroline=False)
fig.update_yaxes(range=[-axis_range, axis_range], zeroline=False, scaleanchor="x", scaleratio=1)
fig.update_layout(
    xaxis_title="Valence (Negative → Positive)",
    yaxis_title="Arousal (Calm → Energetic)",
    legend_title_text='Texture Category',
    hovermode='closest',
    width=None, # Let Dash handle width
    height=700 # Adjust height as needed
)


# --- Initialize Dash App ---
app = dash.Dash(__name__)

# --- App Layout ---
app.layout = html.Div([
    html.H1("Interactive Texture VA Visualization"),
    html.Div([
        # Left Column: Plot
        html.Div([
            dcc.Graph(
                id='va-scatter-plot',
                figure=fig,
                clear_on_unhover=True # Clear hover effects when mouse leaves plot
            )
        ], style={'width': '65%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        # Right Column: Hover Details
        html.Div([
            html.H4("Hover Details"),
            html.Img(id='hover-image', src='', style={'maxWidth': '200px', 'maxHeight': '200px', 'display': 'block', 'margin': 'auto'}),
            html.Pre(id='hover-data', style={'paddingTop': '10px', 'fontSize': '12px'}) # Preformatted text
        ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingLeft': '20px'})

    ], style={'display': 'flex'})
])

# --- Callback for Hover Interaction ---
@app.callback(
    Output('hover-image', 'src'),
    Output('hover-data', 'children'),
    Input('va-scatter-plot', 'hoverData')
)
def display_hover_data(hoverData):
    if hoverData is None:
        # Return default placeholder image and text
        return "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", "Hover over a point to see details."

    try:
        # Get data for the hovered point
        point_index = hoverData['points'][0]['pointIndex']
        point_data = df.iloc[point_index]

        # Encode the image
        image_path = point_data['image_path']
        img_src = encode_image_as_base64(image_path, size=(200, 200)) # Larger size for display panel

        # Format the text details
        details = (
            f"Path: {point_data.get('image_path', 'N/A')}\n"
            f"Filename: {point_data.get('filename', 'N/A')}\n"
            f"Category: {point_data.get('category', 'N/A')}\n"
            f"Valence (Norm): {point_data.get('valence_normalized', 'N/A'):.3f}\n"
            f"Arousal (Norm): {point_data.get('arousal_normalized', 'N/A'):.3f}\n"
            f"Valence Score: {point_data.get('valence_score', 'N/A'):.4f}\n"
            f"Arousal Score: {point_data.get('arousal_score', 'N/A'):.4f}\n"
            f"Quadrant: {point_data.get('quadrant', 'N/A')}"
        )
        return img_src, details

    except Exception as e:
        print(f"Error in hover callback: {e}")
        import traceback
        traceback.print_exc()
        # Return placeholder in case of error during callback execution
        return "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", f"Error processing hover data:\n{e}"


# --- Run the App ---
if __name__ == '__main__':
    print(f"Dash app running on http://127.0.0.1:{args.port}/")
    # Use app.run() instead of the deprecated app.run_server()
    app.run(debug=True, port=args.port)
