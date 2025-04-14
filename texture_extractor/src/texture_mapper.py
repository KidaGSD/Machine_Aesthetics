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
import random # Needed for fallback texture assignment

# Note: Removed imports for torch, librosa, emotion_classifier, clap_classifier

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

def parse_classification_results(results_file):
    """Parse the classification_results.txt file to get top emotion per image."""
    # Returns dict: {norm_image_path: top_emotion_label}
    labels = {}
    if not os.path.exists(results_file):
        print(f"Warning: Classification results file not found: {results_file}")
        return labels
    
    print(f"Parsing classification results from {results_file}...")
    current_image = None
    top_emotion = None
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("Image:"):
                    # Save previous image's top emotion if found
                    if current_image and top_emotion:
                        # Normalize path key for consistency
                        labels[os.path.normpath(current_image)] = top_emotion 
                    # Start new image
                    current_image = line[6:].strip()
                    top_emotion = None # Reset for new image
                elif line.startswith("- ") and ":" in line and current_image and top_emotion is None:
                    # This is the first (top) emotion listed for the current image
                    parts = line[2:].split(":", 1)
                    if len(parts) == 2:
                        top_emotion = parts[0].strip()
                        # We only need the top one for this purpose
            # Save the last image's top emotion
            if current_image and top_emotion:
                labels[os.path.normpath(current_image)] = top_emotion
    except Exception as e:
        print(f"Error parsing classification results: {e}")
    
    print(f"Found top classification labels for {len(labels)} images.")
    return labels

class AudioTextureMapper:
    """Maps pre-computed audio emotions (from VAD timeline) to texture emotions."""
    
    def __init__(self,
                 audio_timeline_path=None,
                 high_confidence_textures_path=None,
                 classification_results_path=None, # Path to detailed classification results
                 emotion_mapping_path=None):
        """
        Initialize the audio-texture mapper.

        Args:
            audio_timeline_path (str): Path to the valence_arousal_timeline.csv file.
            high_confidence_textures_path (str): Path to the high_confidence_images.txt file (filtered list).
            classification_results_path (str): Path to the classification_results.txt file (detailed scores).
            emotion_mapping_path (str): Path to JSON mapping valence/arousal ranges to emotion labels.
        """
        self.audio_timeline = None
        self.texture_paths = [] # List of high-confidence texture paths
        self.classified_texture_emotions = {} # Dict: {norm_texture_path: top_emotion_label}
        self.emotion_mapping_vad = { # Default VAD to emotion mapping
            "joy": {"valence": (0.6, 1.0), "arousal": (0.6, 1.0)},
            "peaceful": {"valence": (0.6, 1.0), "arousal": (0.0, 0.4)},
            "surprised": {"valence": (0.5, 0.8), "arousal": (0.8, 1.0)},
            "angry": {"valence": (0.0, 0.4), "arousal": (0.6, 1.0)},
            "fearful": {"valence": (0.0, 0.4), "arousal": (0.4, 0.8)},
            "disgusted": {"valence": (0.0, 0.3), "arousal": (0.3, 0.7)},
            "sad": {"valence": (0.0, 0.4), "arousal": (0.0, 0.4)},
            "serene": {"valence": (0.5, 0.9), "arousal": (0.1, 0.5)}
        }
        
        # Load audio timeline if provided
        if audio_timeline_path and os.path.exists(audio_timeline_path):
            self.load_audio_timeline(audio_timeline_path)
        else:
             print(f"Warning: Audio timeline path not found or not provided: {audio_timeline_path}")
            
        # Load high confidence textures if provided
        if high_confidence_textures_path and os.path.exists(high_confidence_textures_path):
            self.load_texture_paths(high_confidence_textures_path)
        else:
            print(f"Warning: High confidence textures path not found or not provided: {high_confidence_textures_path}")

        # Load VAD emotion mapping if provided
        if emotion_mapping_path and os.path.exists(emotion_mapping_path):
            try:
                with open(emotion_mapping_path, 'r') as f:
                    self.emotion_mapping_vad = json.load(f)
                print(f"Loaded VAD emotion mapping from {emotion_mapping_path}")
            except Exception as e:
                 print(f"Error loading VAD emotion mapping from {emotion_mapping_path}: {e}. Using defaults.")
        else:
            print(f"VAD emotion mapping path not found or not provided: {emotion_mapping_path}. Using defaults.")

        # Load detailed classification results if provided
        if classification_results_path and os.path.exists(classification_results_path):
            # Parse the results file to get {norm_path: top_emotion}
            self.classified_texture_emotions = parse_classification_results(classification_results_path)
        else:
            print(f"Warning: Classification results path not found or not provided: {classification_results_path}. Cannot map textures by classified emotion.")

    def load_audio_timeline(self, timeline_path):
        """Load valence and arousal timeline from CSV."""
        try:
            self.audio_timeline = pd.read_csv(timeline_path)
            # Ensure required columns exist
            if "Start Time (s)" not in self.audio_timeline.columns or \
               "Valence" not in self.audio_timeline.columns or \
               "Arousal" not in self.audio_timeline.columns:
                raise ValueError("Timeline CSV must contain 'Start Time (s)', 'Valence', and 'Arousal' columns.")
            print(f"Loaded audio timeline with {len(self.audio_timeline)} time points from {timeline_path}")
            return self.audio_timeline
        except Exception as e:
            print(f"Error loading audio timeline from {timeline_path}: {e}")
            self.audio_timeline = None
            return None
    
    def load_texture_paths(self, textures_path):
        """Load high confidence texture paths from file."""
        try:
            with open(textures_path, 'r') as f:
                # Store absolute paths for robustness
                base_dir = os.path.dirname(textures_path) # Assume paths in file are relative to file's dir or absolute
                self.texture_paths = []
                for line in f:
                    path = line.strip()
                    if path:
                        # Attempt to resolve path relative to the list file's directory first
                        abs_path = os.path.abspath(os.path.join(base_dir, path))
                        if not os.path.exists(abs_path):
                             # If not found, assume it might be absolute or relative to CWD (less ideal)
                             abs_path = os.path.abspath(path) 
                             
                        if os.path.exists(abs_path):
                            self.texture_paths.append(abs_path)
                        else:
                            print(f"Warning: Texture path from list not found: {abs_path} (original line: {path})")

            print(f"Loaded {len(self.texture_paths)} existing texture paths from {textures_path}")
            return self.texture_paths
        except Exception as e:
            print(f"Error loading texture paths from {textures_path}: {e}")
            self.texture_paths = []
            return []
    
    # Removed load_texture_emotions method as it's replaced by parsing classification results

    def map_va_to_emotion(self, valence, arousal):
        """Map valence and arousal values to emotion labels based on defined ranges."""
        matched_emotions = []
        
        # Ensure values are within [0, 1]
        valence = max(0.0, min(1.0, valence))
        arousal = max(0.0, min(1.0, arousal))

        # Find matching emotions based on VAD ranges
        for emotion, ranges in self.emotion_mapping_vad.items():
            v_range = ranges.get("valence", (0.0, 1.0))
            a_range = ranges.get("arousal", (0.0, 1.0))
            
            if v_range[0] <= valence <= v_range[1] and a_range[0] <= arousal <= a_range[1]:
                matched_emotions.append(emotion)
        
        # If no exact match, find the closest emotion based on Euclidean distance
        if not matched_emotions:
            min_dist = float('inf')
            closest_emotion = None
            for emotion, ranges in self.emotion_mapping_vad.items():
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
    
    def create_emotion_texture_mapping(self):
        """Create a mapping of emotions to available high-confidence textures using classification results."""
        emotion_texture_map = defaultdict(list)
        
        if not self.texture_paths:
             print("Warning: No high-confidence texture paths loaded. Cannot create emotion-texture map.")
             return {}
        if not self.classified_texture_emotions:
             print("Warning: No classified texture emotions loaded. Cannot create emotion-texture map.")
             # If classification results are missing, we cannot proceed with this mapping strategy.
             return {}

        print("Mapping textures using loaded classification results...")
        mapped_count = 0
        unmapped_count = 0
        # Iterate through the high-confidence texture paths
        for texture_path in self.texture_paths:
            # Find the top classified emotion for this path using normalized paths
            norm_path = os.path.normpath(texture_path)
            top_emotion = self.classified_texture_emotions.get(norm_path)

            if top_emotion:
                # Check if the classified emotion is one we care about in the VAD mapping
                # (The VAD mapping keys define the target emotions for the lamp design)
                if top_emotion in self.emotion_mapping_vad:
                    emotion_texture_map[top_emotion].append(texture_path)
                    mapped_count += 1
                # else: # Optional: Log if a classified emotion isn't in our target VAD map
                #    print(f"Texture {os.path.basename(texture_path)} classified as '{top_emotion}', which is not in VAD map {list(self.emotion_mapping_vad.keys())}.")
            else:
                # This case might happen if classification_results.txt doesn't contain an entry
                # for a path listed in high_confidence_images.txt (should be rare if generated together)
                unmapped_count += 1
                # print(f"Warning: No classification result found for high-confidence texture: {texture_path}")
        
        if unmapped_count > 0:
             print(f"Warning: Could not find classification results for {unmapped_count} high-confidence textures.")
        print(f"Mapped {mapped_count} high-confidence textures to VAD emotions based on classification.")

        # Ensure all emotions defined in the VAD mapping have at least some textures assigned
        # If an emotion has no textures after mapping, assign some randomly from the available high-confidence pool
        if not self.texture_paths: return {} # Cannot proceed if no textures loaded at all
             
        for emotion in self.emotion_mapping_vad.keys():
            if not emotion_texture_map[emotion]:
                print(f"Warning: No high-confidence textures were classified as '{emotion}'. Assigning random high-confidence textures.")
                num_to_assign = min(5, len(self.texture_paths)) # Assign up to 5 random textures from the high-conf list
                if num_to_assign > 0:
                     # Ensure we don't sample more than available
                     k = min(num_to_assign, len(self.texture_paths)) 
                     emotion_texture_map[emotion] = random.sample(self.texture_paths, k)
                else:
                     print(f"Error: Cannot assign random textures for '{emotion}' because no high-confidence textures are available.")
        
        return emotion_texture_map
    
    def generate_texture_timeline(self, output_path=None):
        """Generate a timeline of textures based on audio VAD emotions."""
        if self.audio_timeline is None:
            print("Error: Audio timeline not loaded.")
            return None 
        
        if not self.texture_paths:
            print("Error: Texture paths not loaded.")
            return None
        
        # Create the mapping from emotions to lists of texture paths using classification results
        emotion_texture_map = self.create_emotion_texture_mapping()
        if not emotion_texture_map:
             print("Error: Failed to create emotion-texture map.")
             return None

        texture_timeline_data = []
        
        print(f"Generating texture timeline for {len(self.audio_timeline)} time points...")
        for _, row in tqdm(self.audio_timeline.iterrows(), total=len(self.audio_timeline), desc="Mapping Audio to Textures"):
            time_point = row["Start Time (s)"]
            valence = row["Valence"]
            arousal = row["Arousal"]
            
            # Map VAD values to one or more emotion labels from our VAD map
            current_emotions = self.map_va_to_emotion(valence, arousal)
            
            selected_textures_info = []
            if current_emotions:
                weight_per_emotion = 1.0 / len(current_emotions) 
                
                for emotion in current_emotions:
                    available_textures = emotion_texture_map.get(emotion) # Get textures classified for this emotion
                    if available_textures:
                        selected_texture_path = random.choice(available_textures)
                        selected_textures_info.append({
                            "texture_path": selected_texture_path,
                            "emotion": emotion, # The target VAD emotion
                            "weight": weight_per_emotion 
                        })
                    else:
                         # This should only happen now if the random fallback assignment failed
                         print(f"Critical Warning: No textures available for selected emotion '{emotion}' at time {time_point}, even after fallback.")

            texture_timeline_data.append({
                "time": time_point,
                "valence": valence,
                "arousal": arousal,
                "emotions": current_emotions, 
                "textures": selected_textures_info 
            })
        
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
            valences = [entry["valence"] for entry in texture_timeline]
            arousals = [entry["arousal"] for entry in texture_timeline]
            
            ax1.plot(times, valences, 'b-', label='Valence')
            ax1.plot(times, arousals, 'r-', label='Arousal')
            ax1.set_xlabel('Time (s)'); ax1.set_ylabel('Value (0-1)')
            ax1.set_title('Audio Valence and Arousal Over Time'); ax1.legend(); ax1.grid(True)
            ax1.set_ylim(0, 1) 
            
            emotion_counts = defaultdict(int)
            for entry in texture_timeline:
                for emotion in entry["emotions"]:
                    emotion_counts[emotion] += 1
            
            if emotion_counts:
                emotions_found = sorted(emotion_counts.keys())
                counts = [emotion_counts[e] for e in emotions_found]
                ax2.bar(emotions_found, counts)
                ax2.set_xlabel('Selected Emotion'); ax2.set_ylabel('Frequency (Time Points)')
                ax2.set_title('Distribution of Selected Emotions in Timeline')
                plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
            else:
                 ax2.text(0.5, 0.5, "No emotions mapped", ha='center', va='center')
                 ax2.set_title('Distribution of Selected Emotions in Timeline')

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
