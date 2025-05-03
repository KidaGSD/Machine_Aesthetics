import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Wedge, Circle, FancyBboxPatch, Patch
from matplotlib.colors import LinearSegmentedColormap
import os

# Define the detailed VAD-to-texture mapping
VAD_TEXTURE_MAPPING = {
    "valence_thresholds": [0.4, 0.6],  # Negative < 0.4 <= Neutral < 0.6 <= Positive
    "arousal_thresholds": [0.4, 0.6],  # Low < 0.4 <= Moderate < 0.6 <= High
    "dominance_threshold": 0.5,        # Low < 0.5 <= High
    
    "mapping": {
        "negative_high": [
            "spiky", "jagged", "sharp edges", "torn edges", 
            "chaotic scribbles", "disruptive lines", "erratic lines",
            "fractured patterns", "high-contrast", "thunder-like impact"
        ],
        
        "neutral_high": [
            "dynamic wave", "hint of tension", "vibrant swirl", 
            "neutral tone", "geometric patterns", "taut but not harsh",
            "subtle pulsing", "balanced extremes"
        ],
        
        "positive_high": [
            "explosive swirl", "bursting patterns", "energetic patterns",
            "bright bursts", "intense highlights", "bold dynamic lines",
            "radiating effect", "high saturation", "radiating finish"
        ],
        
        "negative_moderate": [
            "somber", "subdued texture", "melancholic brushstrokes",
            "mild cracks", "fine fractures", "understated fractures",
            "subtle grainy patterns", "minimal light/dark contrast"
        ],
        
        "neutral_moderate": [
            "balanced wave", "uniform ripples", "moderate motion",
            "moderate swirl", "gentle dynamic accents", "quiet strokes",
            "understated texture", "soft medium contrast pattern"
        ],
        
        "positive_moderate": [
            "soft flow", "gentle texture", "elegant texture",
            "mild radiant lines", "delicate pastel effect",
            "subtle warm glow", "smooth finish"
        ],
        
        "negative_low": [
            "dull", "flat", "stagnation", "lifeless",
            "heavy gloom", "deep low contrast", "muted colors",
            "faded finish", "weathered finish"
        ],
        
        "neutral_low": [
            "softly blurred", "subtle texture", "almost monotone",
            "low contrast", "misty effects", "light fog",
            "gentle fade", "gradual transitions", "restrained texture"
        ],
        
        "positive_low": [
            "smooth pastel gradient", "calm transitions", "flowing transitions",
            "flowing wave", "water-like movement", "serene swirl",
            "light", "airy", "refreshing visual impression"
        ]
    },
    
    "dominance_modifiers": {
        "high": [
            "bold", "structured", "organized patterns", "strong lines", 
            "symmetry", "confident", "decisive", "prominent", 
            "defined boundaries", "distinct zones", "color blocks"
        ],
        "low": [
            "fragmented", "scattered", "randomized", "broken lines", 
            "diffuse", "soft edges", "cloud-like", "smeared appearance", 
            "fluid", "melting", "flowing together", "uncontrollable", "organic randomness"
        ]
    }
}

def visualize_vad_mapping():
    """Create a standard visualization of the VAD-to-texture mapping with clear representation of V-A-D vectors."""
    # Set up figure with a standard white background
    plt.style.use('default')
    fig = plt.figure(figsize=(14, 10), facecolor='white')
    
    # Create main grid for the valence-arousal grid
    gs = plt.GridSpec(1, 2, width_ratios=[3, 1], figure=fig)
    ax_grid = fig.add_subplot(gs[0])
    
    # Set up a 3x3 grid
    valence_labels = ["Negative", "Neutral", "Positive"]
    arousal_labels = ["High", "Moderate", "Low"]
    
    # Better color scheme for cells - color represents the valence-arousal combinations
    colors = [
        ["#ffcccb", "#ffe0b3", "#c1f0c1"],  # High arousal (Red-Yellow-Green)
        ["#e0b3ff", "#e6e6e6", "#b3ffd9"],  # Moderate arousal (Purple-Gray-Mint)
        ["#b3c6ff", "#b3e0ff", "#c1f0f0"]   # Low arousal (Blue-Cyan-Teal)
    ]
    
    # Draw the grid with cell text
    cell_width, cell_height = 1, 1
    
    # Create a custom colormap for dominance visual indication
    # This will be used in the cell borders to subtly indicate dominance influence
    high_dom_color = '#3498db'  # Blue for high dominance
    low_dom_color = '#e74c3c'   # Red for low dominance
    
    for i, arousal in enumerate(arousal_labels):
        # Y-axis label positioning with more space
        ax_grid.text(-0.3, 2-i+0.5, arousal, 
                 ha='center', va='center', fontsize=12, fontweight='bold',
                 rotation=90)
        
        for j, valence in enumerate(valence_labels):
            # Create cell key for mapping lookup
            cell_key = f"{valence.lower()}_{arousal.lower()}"
            
            # Draw cell rectangle
            rect = Rectangle((j, 2-i), cell_width, cell_height, 
                            facecolor=colors[i][j], edgecolor='black', 
                            linewidth=1.5, alpha=0.7)
            ax_grid.add_patch(rect)
            
            # Add emotion label at top of cell - with better spacing
            ax_grid.text(j+0.5, 2-i+0.85, cell_key.replace('_', '-').title(), 
                     ha='center', va='center', fontsize=11, fontweight='bold')
            
            # Add texture descriptors with better spacing to avoid overlap
            textures = VAD_TEXTURE_MAPPING["mapping"].get(cell_key, [])
            
            # Calculate available vertical space for descriptors
            available_height = 0.7  # Height available for texture descriptions
            n_descriptors = min(3, len(textures))  # Limit to 3 descriptors for readability
            
            # Calculate spacing between descriptors
            spacing = available_height / (n_descriptors + 1)
            
            for k, texture in enumerate(textures[:n_descriptors]):
                position_y = 2-i+0.7 - ((k+1) * spacing)
                ax_grid.text(j+0.5, position_y, f"• {texture}", 
                         ha='center', va='center', fontsize=9)
    
    # Set axis labels and limits with more space
    ax_grid.set_xlim(-0.5, 3.5)
    ax_grid.set_ylim(-0.5, 3.5)
    ax_grid.set_xticks([0.5, 1.5, 2.5])
    ax_grid.set_xticklabels(valence_labels, fontsize=12)
    ax_grid.set_yticks([])
    
    # Add title and axis labels
    ax_grid.set_title('Emotion-to-Texture Mapping (VAD Model)', fontsize=16, pad=20)
    ax_grid.set_xlabel('Valence (V)', fontsize=14, labelpad=10)
    ax_grid.set_ylabel('Arousal (A)', fontsize=14, labelpad=20)
    
    # Create a separate axis for the Dominance (D) panel
    ax_dom = fig.add_subplot(gs[1])
    ax_dom.axis('off')
    
    # Create visually distinct panels for dominance
    high_dom_panel = Rectangle((0.05, 0.55), 0.9, 0.35, 
                              facecolor=high_dom_color, alpha=0.15,
                              edgecolor=high_dom_color, linewidth=2,
                              zorder=1)
    low_dom_panel = Rectangle((0.05, 0.1), 0.9, 0.35, 
                             facecolor=low_dom_color, alpha=0.15,
                             edgecolor=low_dom_color, linewidth=2,
                             zorder=1)
    
    ax_dom.add_patch(high_dom_panel)
    ax_dom.add_patch(low_dom_panel)
    
    # Add title to dominance panel
    ax_dom.text(0.5, 0.95, "Dominance (D) Vector", 
              ha='center', va='top', fontsize=14, fontweight='bold')
    
    # Add subtitle explaining dominance
    ax_dom.text(0.5, 0.9, "Modifies texture strength/organization", 
              ha='center', va='top', fontsize=10, fontstyle='italic')
    
    # Add high dominance header
    ax_dom.text(0.5, 0.85, "High Dominance", 
              ha='center', va='center', fontsize=12, 
              fontweight='bold', color=high_dom_color)
    
    # Add high dominance modifiers with better spacing
    high_mods = VAD_TEXTURE_MAPPING["dominance_modifiers"]["high"][:5]
    for i, mod in enumerate(high_mods):
        ax_dom.text(0.1, 0.8 - i*0.05, f"• {mod}", 
                  ha='left', va='center', fontsize=10)
    
    # Add low dominance header
    ax_dom.text(0.5, 0.4, "Low Dominance", 
              ha='center', va='center', fontsize=12, 
              fontweight='bold', color=low_dom_color)
    
    # Add low dominance modifiers with better spacing
    low_mods = VAD_TEXTURE_MAPPING["dominance_modifiers"]["low"][:5]
    for i, mod in enumerate(low_mods):
        ax_dom.text(0.1, 0.35 - i*0.05, f"• {mod}", 
                  ha='left', va='center', fontsize=10)
    
    # Add example section
    example_box = Rectangle((0.05, 0.015), 0.9, 0.075, 
                          facecolor='#f8f9fa', alpha=0.8,
                          edgecolor='#666666', linewidth=1,
                          zorder=1)
    ax_dom.add_patch(example_box)
    
    # Add example text
    ax_dom.text(0.5, 0.075, "Example Modification", 
              ha='center', va='center', fontsize=9, 
              fontweight='bold')
    
    # Add specific examples
    ax_dom.text(0.1, 0.05, "Angry (neg-high) + high dom:", 
              ha='left', va='center', fontsize=8)
    ax_dom.text(0.1, 0.025, "\"Structured spiky texture with bold lines\"", 
              ha='left', va='center', fontsize=8, color=high_dom_color)
    
    # Add threshold information at the bottom
    threshold_box = Rectangle((0.05, -0.075), 0.9, 0.065, 
                           facecolor='#f8f9fa', alpha=0.8,
                           edgecolor='#666666', linewidth=1,
                           zorder=1)
    ax_dom.add_patch(threshold_box)
    
    # Add VAD score thresholds
    v_thresholds = VAD_TEXTURE_MAPPING['valence_thresholds']
    a_thresholds = VAD_TEXTURE_MAPPING['arousal_thresholds']
    d_threshold = VAD_TEXTURE_MAPPING['dominance_threshold']
    
    threshold_text = f"V thresholds: <{v_thresholds[0]}=Neg, >{v_thresholds[1]}=Pos\n"
    threshold_text += f"A thresholds: <{a_thresholds[0]}=Low, >{a_thresholds[1]}=High\n"
    threshold_text += f"D threshold: <{d_threshold}=Low, >{d_threshold}=High"
    
    ax_dom.text(0.5, -0.05, threshold_text, 
              ha='center', va='center', fontsize=8, 
              linespacing=1.3)
    
    # Add arrows to indicate direction on main grid
    arrow_props = dict(arrowstyle='->', linewidth=2, color='#333')
    
    # Arousal arrow (top to bottom = high to low)
    ax_grid.annotate('', xy=(-0.4, 0), xytext=(-0.4, 3),
                 arrowprops=arrow_props)
    ax_grid.text(-0.45, 1.5, 'Decreasing Arousal', rotation=90,
             ha='center', va='center', fontsize=10)
    
    # Valence arrow (left to right = negative to positive)
    ax_grid.annotate('', xy=(3, -0.4), xytext=(0, -0.4),
                 arrowprops=arrow_props)
    ax_grid.text(1.5, -0.45, 'Increasing Valence',
             ha='center', va='center', fontsize=10)
    
    # Add color legend for the grid cells
    plt.figtext(0.05, 0.01, "Cell colors represent the 9 possible V-A combinations (not related to dominance)", 
               fontsize=8, fontstyle='italic')
    
    # Add a title for the entire figure explaining VAD vectors
    plt.suptitle('Texture Classification using Valence-Arousal-Dominance (VAD) Model', 
                fontsize=16, y=0.98)
    
    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    
    # Ensure the config directory exists
    os.makedirs('config', exist_ok=True)
    
    # Save the visualization
    plt.savefig('vad_texture_mapping_visualization.png', dpi=300, bbox_inches='tight')
    
    return fig

# Save the mapping to a JSON file
def save_mapping_to_json(file_path='config/vad_texture_mapping.json'):
    """Save the VAD-to-texture mapping to a JSON file."""
    import os
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w') as f:
        json.dump(VAD_TEXTURE_MAPPING, f, indent=2)
    
    print(f"Mapping saved to {file_path}")

# Main execution
if __name__ == "__main__":
    visualize_vad_mapping()
    save_mapping_to_json()
