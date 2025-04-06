import os
import sys
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
from PIL import Image
from tqdm import tqdm
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use try/except for imports to make the code more resilient
try:
    import audio_analysis.machine_ase.luminote.audio_classifiers.emotion_classifier as emotion_classifier
    EMOTION_CLASSIFIER_AVAILABLE = True
except ImportError:
    print("Warning: Emotion classifier not available. Using fallback.")
    EMOTION_CLASSIFIER_AVAILABLE = False

try:
    import audio_analysis.machine_ase.luminote.audio_classifiers.clap_classifier as clap_classifier
    CLAP_AVAILABLE = True
except ImportError:
    print("Warning: CLAP classifier not available. Some functionality will be limited.")
    CLAP_AVAILABLE = False

class AudioTextureMapper:
    """Maps audio emotions to texture emotions for lamp design generation."""
    
    def __init__(self, 
                 audio_timeline_path=None, 
                 high_confidence_textures_path=None,
                 emotion_mapping_path=None,
                 device="cuda"):
        """
        Initialize the audio-texture mapper.
        
        Args:
            audio_timeline_path: Path to valence_arousal_timeline.csv
            high_confidence_textures_path: Path to high_confidence_images.txt
            emotion_mapping_path: Path to JSON mapping valence/arousal ranges to emotions
            device: Device to use for computation
        """
        self.device = device
        self.audio_timeline = None
        self.texture_paths = []
        self.texture_emotions = {}
        self.emotion_mapping = {
            "joy": {"valence": (0.5, 1.0), "arousal": (0.5, 1.0)},
            "calm": {"valence": (0.5, 1.0), "arousal": (0.0, 0.5)},
            "angry": {"valence": (0.0, 0.5), "arousal": (0.5, 1.0)},
            "sad": {"valence": (0.0, 0.5), "arousal": (0.0, 0.5)}
        }
        
        # Load audio timeline if provided
        if audio_timeline_path and os.path.exists(audio_timeline_path):
            self.load_audio_timeline(audio_timeline_path)
            
        # Load high confidence textures if provided
        if high_confidence_textures_path and os.path.exists(high_confidence_textures_path):
            self.load_texture_paths(high_confidence_textures_path)
            
        # Load emotion mapping if provided
        if emotion_mapping_path and os.path.exists(emotion_mapping_path):
            with open(emotion_mapping_path, 'r') as f:
                self.emotion_mapping = json.load(f)
    
    def load_audio_timeline(self, timeline_path):
        """Load valence and arousal timeline from CSV."""
        self.audio_timeline = pd.read_csv(timeline_path)
        print(f"Loaded audio timeline with {len(self.audio_timeline)} time points")
        return self.audio_timeline
    
    def load_texture_paths(self, textures_path):
        """Load high confidence texture paths from file."""
        with open(textures_path, 'r') as f:
            self.texture_paths = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(self.texture_paths)} texture paths")
        return self.texture_paths
    
    def load_texture_emotions(self, emotions_path):
        """Load pre-computed texture emotions from JSON."""
        with open(emotions_path, 'r') as f:
            self.texture_emotions = json.load(f)
        print(f"Loaded emotions for {len(self.texture_emotions)} textures")
        return self.texture_emotions
    
    def map_va_to_emotion(self, valence, arousal):
        """Map valence and arousal values to emotion labels."""
        matched_emotions = []
        
        # Normalize valence and arousal to [0,1] if they're in [-1,1]
        if valence < 0 or arousal < 0:
            valence = (valence + 1) / 2
            arousal = (arousal + 1) / 2
            
        # Find matching emotions
        for emotion, ranges in self.emotion_mapping.items():
            v_range = ranges["valence"]
            a_range = ranges["arousal"]
            
            if v_range[0] <= valence <= v_range[1] and a_range[0] <= arousal <= a_range[1]:
                matched_emotions.append(emotion)
        
        # Default to closest emotion if no match
        if not matched_emotions:
            # Find closest emotion by Euclidean distance to center of ranges
            distances = {}
            for emotion, ranges in self.emotion_mapping.items():
                v_center = (ranges["valence"][0] + ranges["valence"][1]) / 2
                a_center = (ranges["arousal"][0] + ranges["arousal"][1]) / 2
                distance = np.sqrt((valence - v_center)**2 + (arousal - a_center)**2)
                distances[emotion] = distance
            
            closest_emotion = min(distances, key=distances.get)
            matched_emotions = [closest_emotion]
        
        return matched_emotions
    
    def create_emotion_texture_mapping(self):
        """Create a mapping of emotions to textures."""
        emotion_texture_map = {}
        
        # If texture emotions are not loaded, use the filenames as a fallback
        if not self.texture_emotions:
            print("No pre-computed texture emotions found. Using filename-based mapping.")
            for texture_path in self.texture_paths:
                filename = os.path.basename(texture_path)
                folder_name = os.path.basename(os.path.dirname(texture_path))
                
                # Try to extract emotion from filename or folder name
                for emotion in self.emotion_mapping.keys():
                    if emotion in filename.lower() or emotion in folder_name.lower():
                        if emotion not in emotion_texture_map:
                            emotion_texture_map[emotion] = []
                        emotion_texture_map[emotion].append(texture_path)
        else:
            # Use pre-computed texture emotions
            for texture_path, emotions in self.texture_emotions.items():
                top_emotion = max(emotions, key=emotions.get)
                if top_emotion not in emotion_texture_map:
                    emotion_texture_map[top_emotion] = []
                emotion_texture_map[top_emotion].append(texture_path)
        
        # Ensure all emotions have at least one texture
        for emotion in self.emotion_mapping.keys():
            if emotion not in emotion_texture_map or not emotion_texture_map[emotion]:
                print(f"Warning: No textures found for emotion '{emotion}'. Using random textures.")
                emotion_texture_map[emotion] = np.random.choice(self.texture_paths, 
                                                               size=min(5, len(self.texture_paths)), 
                                                               replace=False).tolist()
        
        return emotion_texture_map
    
    def generate_texture_timeline(self, output_path=None):
        """Generate a timeline of textures based on audio emotions."""
        if self.audio_timeline is None:
            raise ValueError("Audio timeline not loaded.")
        
        if not self.texture_paths:
            raise ValueError("Texture paths not loaded.")
        
        # Create emotion to texture mapping
        emotion_texture_map = self.create_emotion_texture_mapping()
        
        # Create timeline of textures
        texture_timeline = []
        
        for _, row in self.audio_timeline.iterrows():
            time_point = row["Start Time (s)"]
            valence = row["Valence"]
            arousal = row["Arousal"]
            
            # Map valence and arousal to emotions
            emotions = self.map_va_to_emotion(valence, arousal)
            
            # Select a texture for each emotion
            selected_textures = []
            for emotion in emotions:
                if emotion in emotion_texture_map and emotion_texture_map[emotion]:
                    # Select a random texture for this emotion
                    selected_texture = np.random.choice(emotion_texture_map[emotion])
                    selected_textures.append({
                        "texture_path": selected_texture,
                        "emotion": emotion,
                        "weight": 1.0 / len(emotions)  # Equal weight for now
                    })
            
            # Add to timeline
            texture_timeline.append({
                "time": time_point,
                "valence": valence,
                "arousal": arousal,
                "emotions": emotions,
                "textures": selected_textures
            })
        
        # Save timeline if output path is provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(texture_timeline, f, indent=2)
            print(f"Saved texture timeline to {output_path}")
        
        return texture_timeline
    
    def visualize_timeline(self, texture_timeline, output_path=None):
        """Visualize the texture timeline."""
        if not texture_timeline:
            raise ValueError("Texture timeline is empty.")
        
        # Create a figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1, 3]})
        
        # Plot valence and arousal over time
        times = [entry["time"] for entry in texture_timeline]
        valences = [entry["valence"] for entry in texture_timeline]
        arousals = [entry["arousal"] for entry in texture_timeline]
        
        ax1.plot(times, valences, 'b-', label='Valence')
        ax1.plot(times, arousals, 'r-', label='Arousal')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Value')
        ax1.set_title('Valence and Arousal Over Time')
        ax1.legend()
        ax1.grid(True)
        
        # Plot emotion distribution
        emotion_counts = {}
        for entry in texture_timeline:
            for emotion in entry["emotions"]:
                if emotion not in emotion_counts:
                    emotion_counts[emotion] = 0
                emotion_counts[emotion] += 1
        
        emotions = list(emotion_counts.keys())
        counts = [emotion_counts[e] for e in emotions]
        
        ax2.bar(emotions, counts)
        ax2.set_xlabel('Emotion')
        ax2.set_ylabel('Count')
        ax2.set_title('Emotion Distribution')
        
        plt.tight_layout()
        
        # Save figure if output path is provided
        if output_path:
            plt.savefig(output_path)
            print(f"Saved timeline visualization to {output_path}")
        
        plt.close()
        
    def process_audio_file(self, audio_path, output_dir, chunk_duration=10, overlap=5):
        """Process an audio file to generate a texture timeline."""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Import emotion classifier if available
        import torch
        use_emotion_model = False
        try:
            emotion_model = emotion_classifier.EmotionClassifier(
                device=torch.device(self.device if torch.cuda.is_available() else "cpu")
            )
            use_emotion_model = True
        except Exception as e:
            print(f"Warning: Could not initialize emotion model: {e}")
            print("Using fallback audio analysis...")
        
        # Load audio file
        try:
            import librosa
            waveform, sr = librosa.load(audio_path, sr=44100)
        except Exception as e:
            print(f"Error loading audio file: {e}")
            print("Creating synthetic audio signal for testing...")
            sr = 44100
            duration = 60  # 60 seconds synthetic audio
            waveform = np.random.randn(duration * sr)
        
        # Chunking with overlap
        chunk_size = int(chunk_duration * sr)
        hop_size = int((chunk_duration - overlap) * sr)
        
        # Process chunks
        timeline = []
        
        for i in tqdm(range(0, len(waveform), hop_size)):
            chunk = waveform[i:i + chunk_size]
            if len(chunk) < chunk_size:
                # Zero-pad shorter chunks
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            
            # Get emotion features
            try:
                if use_emotion_model:
                    result = emotion_model(chunk, sr)
                    valence = float(result.get("valence", 0))
                    arousal = float(result.get("arousal", 0))
                    dominance = float(result.get("dominance", 0))
                else:
                    # Fallback: use simple audio features to estimate valence/arousal
                    mfcc = librosa.feature.mfcc(y=chunk, sr=sr, n_mfcc=13).mean(axis=1)
                    energy = librosa.feature.rms(y=chunk).mean()
                    spec_contrast = librosa.feature.spectral_contrast(y=chunk, sr=sr).mean()
                    
                    # Map to [0,1] range
                    arousal = min(1.0, max(0.0, float(energy * 5)))  # Energy -> arousal
                    valence = min(1.0, max(0.0, 0.5 + float(spec_contrast / 20)))  # Spectral contrast -> valence
                    dominance = 0.5  # Neutral dominance as fallback
            except Exception as e:
                print(f"Error extracting emotions: {e}")
                # Use fallback random values within reasonable ranges
                valence = 0.5 + (np.random.random() - 0.5) * 0.4  # Random value around 0.5
                arousal = 0.5 + (np.random.random() - 0.5) * 0.4
                dominance = 0.5
            
            timeline.append({
                "Start Time (s)": i / sr,
                "Valence": valence,
                "Arousal": arousal,
                "Dominance": dominance
            })
        
        # Save timeline to CSV
        timeline_df = pd.DataFrame(timeline)
        timeline_path = os.path.join(output_dir, "audio_emotion_timeline.csv")
        timeline_df.to_csv(timeline_path, index=False)
        
        # Load the timeline
        self.audio_timeline = timeline_df
        
        # Make sure texture paths are loaded
        if not self.texture_paths:
            default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "high_confidence_images.txt")
            if os.path.exists(default_path):
                print(f"Loading texture paths from default location: {default_path}")
                self.load_texture_paths(default_path)
        
        if not self.texture_paths:
            raise ValueError("Texture paths not loaded. Please run texture classification first.")
        
        # Generate texture timeline
        texture_timeline_path = os.path.join(output_dir, "texture_timeline.json")
        texture_timeline = self.generate_texture_timeline(texture_timeline_path)
        
        # Visualize timeline
        viz_path = os.path.join(output_dir, "emotion_texture_timeline.png")
        self.visualize_timeline(texture_timeline, viz_path)
        
        return texture_timeline

# Function to run the mapper from command line
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Map audio emotions to textures")
    parser.add_argument("--audio", type=str, required=True, help="Path to audio file")
    parser.add_argument("--timeline", type=str, help="Path to valence_arousal_timeline.csv")
    parser.add_argument("--textures", type=str, help="Path to high_confidence_images.txt")
    parser.add_argument("--emotions", type=str, help="Path to emotion mapping JSON")
    parser.add_argument("--output_dir", type=str, default="results/audio_texture", help="Output directory")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use (cuda/cpu)")
    args = parser.parse_args()
    
    mapper = AudioTextureMapper(
        audio_timeline_path=args.timeline,
        high_confidence_textures_path=args.textures,
        emotion_mapping_path=args.emotions,
        device=args.device
    )
    
    if args.audio and os.path.exists(args.audio):
        # Process audio file
        mapper.process_audio_file(args.audio, args.output_dir)
    else:
        # Generate texture timeline from existing data
        os.makedirs(args.output_dir, exist_ok=True)
        texture_timeline = mapper.generate_texture_timeline(
            os.path.join(args.output_dir, "texture_timeline.json")
        )
        mapper.visualize_timeline(
            texture_timeline, 
            os.path.join(args.output_dir, "emotion_texture_timeline.png")
        )

if __name__ == "__main__":
    main() 