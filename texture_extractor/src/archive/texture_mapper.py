import os
import sys
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm
from pathlib import Path
from collections import defaultdict # Added import
import re # Needed for extract_image_info fallback
import random
import clip # Assuming CLIP is installed and accessible
import torch # Added back for device check

# Note: Removed imports for torch, librosa, emotion_classifier, clap_classifier
# Placeholder for CLIP model loading - needs proper implementation later
# Potentially reuse logic from texture_classifier.py
clip_model = None
clip_preprocess = None
clip_device = "cuda" if torch.cuda.is_available() else "cpu" # Requires torch import back if used here

def load_clip_if_needed():
    global clip_model, clip_preprocess
    if clip_model is None:
        try:
            # This is placeholder logic - adapt from texture_classifier.py
            print("Loading CLIP model for retrieval...")
            clip_model, clip_preprocess = clip.load("ViT-B/32", device=clip_device)
            print("CLIP model loaded.")
        except Exception as e:
            print(f"Error loading CLIP model: {e}")
            clip_model = None # Ensure it stays None if loading fails

# --- Helper Function ---
def extract_image_info(image_path):
    """Extract category and filename from image path (adapted from texture_depth_evaluator)."""
    try:
        parts = image_path.split(os.sep)
        for i, part in enumerate(parts):
            if part == 'images': # Assuming dtd/images structure
                category = parts[i+1]
                filename = parts[i+2]
                return category, os.path.splitext(filename)[0]
    except Exception:
        pass
    try: # Fallback regex
        match = re.search(r'([a-zA-Z-]+)_(\d+)', os.path.basename(image_path))
        if match:
            return match.group(1), match.group(0).split('.')[0]
    except Exception:
        pass
    # Don't print warning here, let the caller handle None
    return None, None

# Removed parse_classification_results as it's no longer the primary mapping method

# --- New Mapping Logic ---

# Define the Valence x Arousal mapping table
# Using simple keywords for now, can be expanded
VAD_TO_KEYWORDS = {
    # High Arousal
    "neg_high": ["Spiky", "Jagged", "Chaotic Scribbles", "Fractured", "High Contrast Thunder"],
    "neu_high": ["Dynamic Wave Tension", "Vibrant Swirl Neutral", "Taut Geometric", "Subtle Pulsing"],
    "pos_high": ["Explosive Swirl", "Bright Bursts", "Bold Dynamic Lines", "Radiating High Saturation"],
    # Moderate Arousal
    "neg_mod": ["Somber Subdued", "Melancholic Brushstrokes", "Mild Cracks", "Subtle Grainy"],
    "neu_mod": ["Balanced Wave", "Moderate Swirl", "Quiet Strokes", "Medium Contrast Pattern"],
    "pos_mod": ["Soft Flow", "Elegant", "Mild Radiant Lines", "Warm Glowing Smooth"],
    # Low Arousal
    "neg_low": ["Dull", "Flat", "Lifeless", "Heavy Gloom", "Muted Weathered"],
    "neu_low": ["Softly Blurred", "Low Contrast Misty", "Gentle Fade"],
    "pos_low": ["Smooth Pastel Gradient", "Flowing Wave Water", "Serene Swirl", "Airy Refreshing"]
}

# Define Dominance modifiers
DOMINANCE_MODIFIERS = {
    "high": ["Bold", "Structured", "Organized", "Defined Boundaries", "Confident Lines"],
    "low": ["Fragmented", "Chaotic", "Diffuse", "Fluid", "Melting", "Scattered"]
}

def get_vad_quadrant(valence, arousal):
    """ Determine the VAD quadrant based on valence and arousal values (0-1). """
    # Define thresholds (adjust as needed)
    v_low_thresh = 0.4
    v_high_thresh = 0.6
    a_low_thresh = 0.4
    a_high_thresh = 0.6

    if arousal >= a_high_thresh:
        if valence <= v_low_thresh: return "neg_high"
        if valence >= v_high_thresh: return "pos_high"
        return "neu_high"
    elif arousal <= a_low_thresh:
        if valence <= v_low_thresh: return "neg_low"
        if valence >= v_high_thresh: return "pos_low"
        return "neu_low"
    else: # Moderate arousal
        if valence <= v_low_thresh: return "neg_mod"
        if valence >= v_high_thresh: return "pos_mod"
        return "neu_mod"

def get_keywords_from_vad(valence, arousal, dominance, overall_emotion="neutral"): # Added overall_emotion parameter
    """ Get descriptive keywords based on valence, arousal, and dominance. """
    # Normalize dominance to low/high (0-1 range assumed)
    dom_thresh = 0.5
    dom_level = "high" if dominance >= dom_thresh else "low"

    # Get base keywords from VAD quadrant
    quadrant = get_vad_quadrant(valence, arousal)
    base_keywords = VAD_TO_KEYWORDS.get(quadrant, [])

    # Get dominance modifier keywords
    modifier_keywords = DOMINANCE_MODIFIERS.get(dom_level, [])

    # Combine and select a few keywords (e.g., 2 base, 1 modifier)
    selected_keywords = []
    if base_keywords:
        selected_keywords.extend(random.sample(base_keywords, min(len(base_keywords), 2)))
    if modifier_keywords:
        selected_keywords.extend(random.sample(modifier_keywords, min(len(modifier_keywords), 1)))

    # --- Add bias based on overall emotion ---
    # Example: If overall is positive, slightly increase chance of positive keywords
    # This is a simple placeholder, more sophisticated biasing is possible
    if overall_emotion in ["joy", "peaceful", "serene", "pos_high", "pos_mod", "pos_low"]: # Map labels if needed
        # Increase chance of sampling from positive quadrants if current quadrant is neutral/neg
        pass # Placeholder for bias logic
    elif overall_emotion in ["angry", "sad", "fearful", "disgusted", "neg_high", "neg_mod", "neg_low"]:
        # Increase chance of sampling from negative quadrants if current is neutral/pos
        pass # Placeholder for bias logic

    return selected_keywords, quadrant # Return quadrant for potential logging/debugging

def generate_clip_prompt(keywords):
    """ Generate a text prompt for CLIP from keywords. """
    if not keywords:
        return "Abstract texture" # Fallback prompt
    # Simple combination for now, can be made more sophisticated
    prompt = f"{', '.join(keywords)} texture pattern"
    return prompt

# Placeholder for actual CLIP retrieval function
# This needs to be implemented, possibly by adapting texture_classifier.py
def find_best_texture_with_clip(prompt, texture_paths):
    """
    Placeholder: Finds the best matching texture path from a list using CLIP.

    Args:
        prompt (str): The text prompt describing the desired texture.
        texture_paths (list): List of candidate texture file paths.

    Returns:
        str: The path to the best matching texture, or None if error/no match.
    """
    print(f"CLIP Retrieval (Placeholder): Searching for prompt: '{prompt}' among {len(texture_paths)} textures.")
    load_clip_if_needed() # Ensure model is loaded
    if not clip_model or not texture_paths:
        print("Warning: CLIP model not loaded or no texture paths provided for retrieval.")
        return random.choice(texture_paths) if texture_paths else None # Fallback: random choice or None

    # --- Start Placeholder CLIP Logic ---
    # This section needs to be replaced with actual CLIP image encoding and comparison
    try:
        # Encode the text prompt
        text_input = clip.tokenize([prompt]).to(clip_device)
        with torch.no_grad():
            text_features = clip_model.encode_text(text_input)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        # Encode a subset of images (for performance in placeholder)
        # In reality, you might pre-compute image features
        num_images_to_check = min(50, len(texture_paths)) # Check a subset
        image_subset_paths = random.sample(texture_paths, num_images_to_check)
        image_features_list = []

        for img_path in image_subset_paths:
             try:
                 image = Image.open(img_path).convert("RGB")
                 image_input = clip_preprocess(image).unsqueeze(0).to(clip_device)
                 with torch.no_grad():
                     img_features = clip_model.encode_image(image_input)
                     img_features /= img_features.norm(dim=-1, keepdim=True)
                     image_features_list.append(img_features)
             except Exception as img_e:
                 print(f"Warning: Could not process image {img_path} for CLIP: {img_e}")
                 image_features_list.append(None) # Add placeholder for failed images

        # Filter out failed encodings
        valid_indices = [i for i, f in enumerate(image_features_list) if f is not None]
        if not valid_indices:
             print("Warning: Could not encode any images for CLIP comparison.")
             return random.choice(texture_paths) # Fallback

        image_features = torch.cat([image_features_list[i] for i in valid_indices], dim=0)
        valid_image_paths = [image_subset_paths[i] for i in valid_indices]

        # Calculate similarity
        similarity = (100.0 * text_features @ image_features.T).softmax(dim=-1)
        best_match_idx = similarity[0].argmax().item()
        best_texture_path = valid_image_paths[best_match_idx]

        print(f"CLIP Retrieval (Placeholder): Best match for '{prompt}' is {os.path.basename(best_texture_path)}")
        return best_texture_path

    except Exception as e:
        print(f"Error during placeholder CLIP retrieval: {e}")
        return random.choice(texture_paths) # Fallback
    # --- End Placeholder CLIP Logic ---


def calculate_vad_distance(vad1, vad2):
    """ Calculates Euclidean distance between two VAD points (dictionaries or tuples). """
    if vad1 is None or vad2 is None:
        return float('inf') # Treat None as infinitely distant

    # Use the chunk values for distance calculation
    v1, a1, d1 = (vad1.get('valence', 0.5), vad1.get('arousal', 0.5), vad1.get('dominance', 0.5))
    v2, a2, d2 = (vad2.get('valence', 0.5), vad2.get('arousal', 0.5), vad2.get('dominance', 0.5))

    # Simple Euclidean distance - weights could be added if needed
    # Ensure values are treated as floats
    return np.sqrt((float(v1) - float(v2))**2 + (float(a1) - float(a2))**2 + (float(d1) - float(d2))**2)


class AudioTextureMapper:
    """Maps pre-computed audio emotions (VAD) to textures using descriptive keywords and CLIP retrieval."""

    def __init__(self,
                 audio_timeline_path=None,
                 texture_dataset_path=None, # Path to the folder containing texture images
                 emotion_mapping_path=None, # VAD range mapping (optional, uses defaults)
                 overall_emotion="neutral"): # Added overall emotion
        """
        Initialize the audio-texture mapper using dynamic CLIP retrieval.

        Args:
            audio_timeline_path (str): Path to the valence_arousal_dominance_timeline.csv file.
            texture_dataset_path (str): Path to the root directory of texture images (e.g., .../hugging_data/color).
            emotion_mapping_path (str): Path to JSON defining VAD ranges for fallback/debugging (optional).
            overall_emotion (str): The dominant emotion label for the entire audio clip.
        """
        self.audio_timeline = None
        self.texture_dataset_path = texture_dataset_path
        self.all_texture_paths = [] # List of all available texture paths in the dataset
        self.overall_emotion = overall_emotion # Store overall emotion (passed from main.py)
        self.overall_vad = None # Store overall VAD from timeline
        self.emotion_mapping_vad = { # Default VAD to emotion mapping (used for fallback/closest match)
            "joy": {"valence": [0.6, 1.0], "arousal": [0.6, 1.0]},
            "peaceful": {"valence": [0.6, 1.0], "arousal": [0.0, 0.4]},
            "surprised": {"valence": [0.5, 0.8], "arousal": [0.8, 1.0]},
            "angry": {"valence": [0.0, 0.4], "arousal": [0.6, 1.0]},
            "fearful": {"valence": [0.0, 0.4], "arousal": [0.4, 0.8]},
            "disgusted": {"valence": [0.0, 0.3], "arousal": [0.3, 0.7]},
            "sad": {"valence": [0.0, 0.4], "arousal": [0.0, 0.4]},
            "serene": {"valence": [0.5, 0.9], "arousal": [0.1, 0.5]}
        }

        # Load audio timeline if provided
        if audio_timeline_path and os.path.exists(audio_timeline_path):
            self.load_audio_timeline(audio_timeline_path)
        else:
             print(f"Warning: Audio timeline path not found or not provided: {audio_timeline_path}")

        # Find all textures in the dataset path
        if self.texture_dataset_path and os.path.isdir(self.texture_dataset_path):
            self.find_all_textures()
        else:
            print(f"Warning: Texture dataset path not found or not a directory: {self.texture_dataset_path}")

        # Load VAD emotion mapping if provided (used for fallback)
        if emotion_mapping_path and os.path.exists(emotion_mapping_path):
            try:
                # Load only the VAD range part, ignore other keys
                with open(emotion_mapping_path, 'r') as f:
                    full_mapping = json.load(f)
                # Filter to keep only entries where value is a dict (likely VAD ranges)
                self.emotion_mapping_vad = {k: v for k, v in full_mapping.items() if isinstance(v, dict) and 'valence' in v and 'arousal' in v}
                print(f"Loaded VAD emotion mapping ranges from {emotion_mapping_path}")
            except Exception as e:
                 print(f"Error loading VAD emotion mapping from {emotion_mapping_path}: {e}. Using defaults.")
        else:
            print(f"VAD emotion mapping path not found or not provided: {emotion_mapping_path}. Using defaults.")

        # Ensure CLIP model is loaded (or attempted) once
        load_clip_if_needed()

    def load_audio_timeline(self, timeline_path):
        """Load VAD timeline from CSV, including chunk and overall values."""
        try:
            self.audio_timeline = pd.read_csv(timeline_path)
            # Ensure required columns exist (using new names, including discrete emotion)
            required_cols = ["Start Time (s)", "ChunkValence", "ChunkArousal", "ChunkDominance", "ChunkDiscreteEmotion",
                             "OverallValence", "OverallArousal", "OverallDominance", "OverallDiscreteEmotion"]
            if not all(col in self.audio_timeline.columns for col in required_cols):
                # Fallback to old column names for compatibility (without discrete emotion)
                required_cols_old = ["Start Time (s)", "ChunkValence", "ChunkArousal", "ChunkDominance",
                                     "OverallValence", "OverallArousal", "OverallDominance"]
                required_cols_legacy = ["Start Time (s)", "Valence", "Arousal", "Dominance"]

                if all(col in self.audio_timeline.columns for col in required_cols_old):
                     print("Warning: Using VAD timeline format without discrete emotion column.")
                     # Add dummy discrete emotion column if missing
                     if "ChunkDiscreteEmotion" not in self.audio_timeline.columns:
                         self.audio_timeline["ChunkDiscreteEmotion"] = "neutral" # Assign neutral default
                     if "OverallDiscreteEmotion" not in self.audio_timeline.columns:
                         self.audio_timeline["OverallDiscreteEmotion"] = "neutral"

                elif all(col in self.audio_timeline.columns for col in required_cols_legacy):
                    # This block needs indentation
                    print("Warning: Using legacy VAD timeline format. Renaming columns.")
                    self.audio_timeline.rename(columns={
                        "Valence": "ChunkValence",
                        "Arousal": "ChunkArousal",
                        "Dominance": "ChunkDominance"
                    }, inplace=True)
                    # Add dummy overall and discrete columns if missing
                    if "OverallValence" not in self.audio_timeline.columns: self.audio_timeline["OverallValence"] = 0.5
                    if "OverallArousal" not in self.audio_timeline.columns: self.audio_timeline["OverallArousal"] = 0.5
                    if "OverallDominance" not in self.audio_timeline.columns: self.audio_timeline["OverallDominance"] = 0.5
                    if "ChunkDiscreteEmotion" not in self.audio_timeline.columns: self.audio_timeline["ChunkDiscreteEmotion"] = "neutral"
                    if "OverallDiscreteEmotion" not in self.audio_timeline.columns: self.audio_timeline["OverallDiscreteEmotion"] = "neutral"
                else:
                    raise ValueError(f"Timeline CSV must contain columns like {required_cols} or {required_cols_legacy}.")

            print(f"Loaded audio timeline with {len(self.audio_timeline)} time points from {timeline_path}")

            # Store the overall VAD from the first row (should be the same for all rows)
            if not self.audio_timeline.empty:
                self.overall_vad = {
                    "valence": self.audio_timeline.iloc[0]["OverallValence"],
                    "arousal": self.audio_timeline.iloc[0]["OverallArousal"],
                    "dominance": self.audio_timeline.iloc[0]["OverallDominance"]
                }
                print(f"Overall VAD from timeline: {self.overall_vad}")

            # Normalize Chunk VAD values to 0-1 range if they aren't already
            for col in ["ChunkValence", "ChunkArousal", "ChunkDominance"]:
                 if col in self.audio_timeline.columns and (self.audio_timeline[col].min() < 0.0 or self.audio_timeline[col].max() > 1.0):
                      print(f"Normalizing {col} column from [{self.audio_timeline[col].min():.3f}, {self.audio_timeline[col].max():.3f}] to [0, 1]")
                      # Simple min-max scaling
                      min_val = self.audio_timeline[col].min()
                      max_val = self.audio_timeline[col].max()
                      if max_val > min_val:
                           self.audio_timeline[col] = (self.audio_timeline[col] - min_val) / (max_val - min_val)
                      else: # Handle case where all values are the same
                           self.audio_timeline[col] = 0.5 # Assign neutral midpoint
            return self.audio_timeline
        except Exception as e:
            print(f"Error loading audio timeline from {timeline_path}: {e}")
            self.audio_timeline = None
            return None

    def find_all_textures(self):
        """ Find all image files in the texture dataset directory. """
        self.all_texture_paths = []
        valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
        print(f"Scanning for textures in: {self.texture_dataset_path}")
        for root, _, files in os.walk(self.texture_dataset_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in valid_extensions):
                    self.all_texture_paths.append(os.path.join(root, file))
        print(f"Found {len(self.all_texture_paths)} total textures in dataset.")
        if not self.all_texture_paths:
             print("Warning: No textures found in the specified dataset path!")

    def map_va_to_emotion(self, valence, arousal):
        """Map valence and arousal values to emotion labels based on defined ranges (used as fallback)."""
        matched_emotions = []
        
        # Ensure values are within [0, 1]
        valence = max(0.0, min(1.0, valence))
        arousal = max(0.0, min(1.0, arousal))

        # Find matching emotions based on VAD ranges
        for emotion, ranges in self.emotion_mapping_vad.items():
            # Skip items that are not dictionaries (like default_weight)
            if not isinstance(ranges, dict):
                continue

            v_range = ranges.get("valence", (0.0, 1.0))
            a_range = ranges.get("arousal", (0.0, 1.0))

            if v_range[0] <= valence <= v_range[1] and a_range[0] <= arousal <= a_range[1]:
                matched_emotions.append(emotion)

        # If no exact match, find the closest emotion based on Euclidean distance
        if not matched_emotions:
            min_dist = float('inf')
            closest_emotion = None
            for emotion, ranges in self.emotion_mapping_vad.items():
                # Skip items that are not dictionaries
                if not isinstance(ranges, dict):
                    continue
                v_center = (ranges.get("valence", (0.0, 1.0))[0] + ranges.get("valence", (0.0, 1.0))[1]) / 2
                a_center = (ranges.get("arousal", (0.0, 1.0))[0] + ranges.get("arousal", (0.0, 1.0))[1]) / 2
                distance = np.sqrt((valence - v_center)**2 + (arousal - a_center)**2)
                if distance < min_dist:
                    min_dist = distance
                    closest_emotion = emotion

            if closest_emotion:
                matched_emotions = [closest_emotion]
            else: # Fallback if mapping is empty
                 matched_emotions = ["neutral"]

        return matched_emotions

    # Removed create_emotion_texture_mapping as it's replaced by dynamic retrieval

    def generate_texture_timeline(self, output_path=None):
        """Generate a timeline of textures based on audio VAD+Dominance using CLIP retrieval."""
        if self.audio_timeline is None:
            print("Error: Audio timeline not loaded.")
            return None

        if not self.all_texture_paths:
            print("Error: No texture paths found in the dataset directory.")
            return None

        texture_timeline_data = []
        print(f"Generating texture timeline for {len(self.audio_timeline)} time points using CLIP retrieval (only on transitions)...")

        # State variables for the last identified KEYFRAME (based on smoothed data)
        last_keyframe_smoothed_quadrant = None
        last_keyframe_smoothed_dom_level = None
        last_keyframe_smoothed_discrete_emotion = None
        last_keyframe_texture_path = None
        last_keyframe_smoothed_vad = None # Store smoothed VAD of last keyframe

        clip_searches_performed = 0
        SMOOTHING_WINDOW = 15 # Number of frames for rolling average (e.g., 15 frames = 7.5 seconds)
        VAD_DRIFT_THRESHOLD = 0.25 # Threshold for significant VAD drift from last keyframe (tune this)

        # Calculate smoothed VAD values first
        vad_cols = ["ChunkValence", "ChunkArousal", "ChunkDominance"]
        smoothed_vad_df = self.audio_timeline[vad_cols].rolling(window=SMOOTHING_WINDOW, center=True, min_periods=1).mean()
        # Handle potential NaN at edges if needed, e.g., forward/backward fill
        smoothed_vad_df = smoothed_vad_df.fillna(method='bfill').fillna(method='ffill')

        # Calculate smoothed discrete emotion based on smoothed VAD
        # Need to re-apply the mapping logic used in valence-analysis.py
        # This assumes the mapping function `map_va_to_emotion` is available or redefined here
        # For simplicity, let's assume it's available (or copy it here if needed)
        # Note: map_va_to_emotion expects VAD in [-1, 1], but our timeline is [0, 1] after normalization.
        # We need to either adjust the mapping function or denormalize before calling.
        # Let's adjust the mapping function thresholds to work with [0, 1] range directly.
        # (Assuming get_vad_quadrant and map_va_to_emotion work with 0-1 range)

        smoothed_emotions = []
        smoothed_quadrants = []
        smoothed_dom_levels = []
        dom_thresh = 0.5 # Match threshold in get_keywords_from_vad

        print(f"Calculating smoothed states over window size {SMOOTHING_WINDOW}...")
        for index, smoothed_row in smoothed_vad_df.iterrows():
            s_valence = smoothed_row["ChunkValence"]
            s_arousal = smoothed_row["ChunkArousal"]
            s_dominance = smoothed_row["ChunkDominance"] # Use smoothed dominance too

            s_quadrant = get_vad_quadrant(s_valence, s_arousal)
            s_dom_level = "high" if s_dominance >= dom_thresh else "low"
            # Use the same mapping logic as valence-analysis.py (ensure it handles 0-1 range)
            # Re-defining map_va_to_emotion locally for clarity if needed, or ensure it's imported correctly
            # Assuming map_va_to_emotion is defined above and works with 0-1
            s_discrete_emotion = self.map_va_to_emotion(s_valence, s_arousal) # Use instance method

            smoothed_quadrants.append(s_quadrant)
            smoothed_dom_levels.append(s_dom_level)
            smoothed_emotions.append(s_discrete_emotion)

        print("Smoothed states calculated.")

        for i, row in tqdm(enumerate(self.audio_timeline.iterrows()), total=len(self.audio_timeline), desc="Mapping Audio to Textures"):
            idx, data_row = row # Get index and data
            time_point = data_row["Start Time (s)"]

            # Get current chunk's RAW VAD for keyword generation
            valence = data_row["ChunkValence"]
            arousal = data_row["ChunkArousal"]
            dominance = data_row["ChunkDominance"]

            # Get current frame's SMOOTHED state
            current_smoothed_quadrant = smoothed_quadrants[i]
            current_smoothed_dom_level = smoothed_dom_levels[i]
            current_smoothed_discrete_emotion = smoothed_emotions[i]
            current_smoothed_vad = {
                "valence": smoothed_vad_df.iloc[i]["ChunkValence"],
                "arousal": smoothed_vad_df.iloc[i]["ChunkArousal"],
                "dominance": smoothed_vad_df.iloc[i]["ChunkDominance"]
            }

            # Compare current smoothed state with the LAST KEYFRAME's smoothed state
            is_first_or_last = (i == 0 or i == len(self.audio_timeline) - 1)
            smoothed_state_changed = (
                current_smoothed_quadrant != last_keyframe_smoothed_quadrant
                or current_smoothed_dom_level != last_keyframe_smoothed_dom_level
                or current_smoothed_discrete_emotion != last_keyframe_smoothed_discrete_emotion
            )

            # Calculate VAD distance drift from LAST KEYFRAME's smoothed VAD
            vad_distance_drift = calculate_vad_distance(current_smoothed_vad, last_keyframe_smoothed_vad)
            significant_drift = (vad_distance_drift > VAD_DRIFT_THRESHOLD)

            # Determine if a new search is needed
            # Search if: first/last frame OR smoothed state changed OR significant drift from last keyframe VAD
            needs_new_search = is_first_or_last or smoothed_state_changed or significant_drift

            if needs_new_search:
                # Use the RAW VAD of the current chunk for keyword generation
                keywords, _ = get_keywords_from_vad(valence, arousal, dominance, self.overall_emotion)
                prompt = generate_clip_prompt(keywords)

                # Find best matching texture using CLIP
                selected_texture_path = find_best_texture_with_clip(prompt, self.all_texture_paths)
                clip_searches_performed += 1

                # Fallback if CLIP fails or returns None
                if not selected_texture_path:
                     print(f"Warning: CLIP retrieval failed for prompt '{prompt}' at time {time_point}. Using random texture.")
                     selected_texture_path = random.choice(self.all_texture_paths) if self.all_texture_paths else None

                # Update last KEYFRAME state variables using SMOOTHED values
                last_keyframe_texture_path = selected_texture_path
                last_keyframe_smoothed_quadrant = current_smoothed_quadrant
                last_keyframe_smoothed_dom_level = current_smoothed_dom_level
                last_keyframe_smoothed_discrete_emotion = current_smoothed_discrete_emotion
                last_keyframe_smoothed_vad = current_smoothed_vad # Store the smoothed VAD of this keyframe
            else:
                # State hasn't changed significantly, reuse the last keyframe's texture
                selected_texture_path = last_keyframe_texture_path
                # Get keywords and prompt for logging (using raw VAD)
                keywords, _ = get_keywords_from_vad(valence, arousal, dominance, self.overall_emotion)
                prompt = generate_clip_prompt(keywords)

            # Ensure we have a path, even if reusing failed previously or first frame had no texture
            if not selected_texture_path and self.all_texture_paths:
                 # Fallback to random if no texture assigned yet
                 selected_texture_path = random.choice(self.all_texture_paths)
                 # If it's the first frame, make sure keyframe state is updated
                 if i == 0:
                      last_keyframe_texture_path = selected_texture_path
                      last_keyframe_smoothed_quadrant = current_smoothed_quadrant
                      last_keyframe_smoothed_dom_level = current_smoothed_dom_level
                      last_keyframe_smoothed_discrete_emotion = current_smoothed_discrete_emotion
                      last_keyframe_smoothed_vad = current_smoothed_vad


            # Store the retrieved/reused texture path and other info
            texture_timeline_data.append({
                "time": time_point,
                "valence": valence, # Store chunk valence
                "arousal": arousal, # Store chunk arousal
                "dominance": dominance, # Store chunk dominance
                "discrete_emotion": data_row.get("ChunkDiscreteEmotion", "neutral"), # Store original discrete emotion
                "vad_quadrant": get_vad_quadrant(valence, arousal), # Store original quadrant
                "smoothed_valence": current_smoothed_vad["valence"], # Store smoothed VAD
                "smoothed_arousal": current_smoothed_vad["arousal"],
                "smoothed_dominance": current_smoothed_vad["dominance"],
                "smoothed_discrete_emotion": current_smoothed_discrete_emotion, # Store smoothed emotion
                "smoothed_vad_quadrant": current_smoothed_quadrant, # Store smoothed quadrant
                "keywords": keywords,
                "clip_prompt": prompt,
                "textures": [{"texture_path": selected_texture_path, "weight": 1.0}] if selected_texture_path else [] # Handle case where no texture could be found/assigned
            })

        print(f"CLIP searches performed: {clip_searches_performed} (out of {len(self.audio_timeline)} time points)")

        if output_path:
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(texture_timeline_data, f, indent=2)
                print(f"Saved texture timeline to {output_path}")
            except Exception as e:
                print(f"Error saving texture timeline to {output_path}: {e}")
        
        return texture_timeline_data
    
    def visualize_timeline(self, texture_timeline, output_path=None):
        """Visualize the VAD timeline and the distribution of selected emotions."""
        if not texture_timeline:
            print("Warning: Cannot visualize empty texture timeline.")
            return
        
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [2, 1]})
            
            times = [entry["time"] for entry in texture_timeline]
            # Plot Smoothed VAD
            valences = [entry["smoothed_valence"] for entry in texture_timeline]
            arousals = [entry["smoothed_arousal"] for entry in texture_timeline]
            dominances = [entry["smoothed_dominance"] for entry in texture_timeline] # Get dominance too

            ax1.plot(times, valences, 'b-', label='Smoothed Valence')
            ax1.plot(times, arousals, 'r-', label='Smoothed Arousal')
            ax1.plot(times, dominances, 'g--', label='Smoothed Dominance', alpha=0.7) # Plot dominance
            ax1.set_xlabel('Time (s)'); ax1.set_ylabel('Value (0-1)')
            ax1.set_title(f'Smoothed Audio VAD Over Time (Window={SMOOTHING_WINDOW})'); ax1.legend(); ax1.grid(True)
            ax1.set_ylim(0, 1)

            # Visualize emotion distribution based on smoothed discrete emotions
            emotion_counts = defaultdict(int)
            for entry in texture_timeline:
                # Use the smoothed discrete emotion stored in the timeline entry
                emotion = entry.get("smoothed_discrete_emotion", "unknown")
                emotion_counts[emotion] += 1

            if emotion_counts:
                emotions_found = sorted(emotion_counts.keys())
                counts = [emotion_counts[e] for e in emotions_found]
                ax2.bar(emotions_found, counts)
                ax2.set_xlabel('Smoothed Emotion'); ax2.set_ylabel('Frequency (Time Points)')
                ax2.set_title('Distribution of Smoothed Emotions in Timeline')
                plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
            else:
                 ax2.text(0.5, 0.5, "No emotions mapped", ha='center', va='center')
                 ax2.set_title('Distribution of Smoothed Emotions in Timeline')

            plt.tight_layout()
            
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                plt.savefig(output_path)
                print(f"Saved timeline visualization to {output_path}")
            
            plt.close(fig) 
        except Exception as e:
            print(f"Error visualizing timeline: {e}")

# Removed process_audio_file method
# Removed the main() block
