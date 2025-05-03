import os
import csv
import librosa
import numpy as np
import torch
from pydub import AudioSegment
from audio_classifiers.emotion_classifier import EmotionClassifier
import argparse

# === Argument parsing ===
parser = argparse.ArgumentParser(description="Extract VAD timeline from audio.")
parser.add_argument("--input", type=str, help="Path to input audio file (wav or mp3)")
parser.add_argument("--output", type=str, help="Path to output CSV file")
args = parser.parse_args()

# === Set your audio file path here (default if not provided) ===
input_path = args.input if args.input else os.path.join(os.path.dirname(__file__), "audio", "sudden-angry.wav")

# === Auto-convert MP3 to WAV if needed ===
if input_path.lower().endswith(".mp3"):
    print("🎧 Converting .mp3 to .wav...")
    wav_path = input_path.replace(".mp3", ".wav")
    audio = AudioSegment.from_mp3(input_path)
    audio.export(wav_path, format="wav")
    audio_path = wav_path
else:
    audio_path = input_path

# === Config ===
output_csv = args.output if args.output else os.path.join(os.path.dirname(__file__), "valence_arousal_timeline-angry.csv")
sampling_rate = 44100
chunk_duration_sec = 0.5

# === Load audio ===
print(f"🔊 Loading audio from: {audio_path}")
waveform, sr = librosa.load(audio_path, sr=sampling_rate)

# === Set up emotion classifier ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
emotion_classifier = EmotionClassifier(device)

# === Calculate Overall Emotion for the entire audio ===
print("📊 Calculating overall emotion...")
overall_result = emotion_classifier(waveform, sr)
overall_valence = overall_result.get("valence", 0.0)
overall_arousal = overall_result.get("arousal", 0.0)
# Estimate overall dominance (can be refined later)
overall_dominance = np.tanh((overall_valence + overall_arousal) / 2)
print(f"Overall VAD: V={overall_valence:.3f}, A={overall_arousal:.3f}, D={overall_dominance:.3f}")

# === VAD to Discrete Emotion Mapping (copied from texture_mapper.py logic) ===
# Default VAD to emotion mapping ranges
emotion_mapping_vad = {
    "joy": {"valence": [0.6, 1.0], "arousal": [0.6, 1.0]},
    "peaceful": {"valence": [0.6, 1.0], "arousal": [0.0, 0.4]},
    "surprised": {"valence": [0.5, 0.8], "arousal": [0.8, 1.0]},
    "angry": {"valence": [0.0, 0.4], "arousal": [0.6, 1.0]},
    "fearful": {"valence": [0.0, 0.4], "arousal": [0.4, 0.8]},
    "disgusted": {"valence": [0.0, 0.3], "arousal": [0.3, 0.7]},
    "sad": {"valence": [0.0, 0.4], "arousal": [0.0, 0.4]},
    "serene": {"valence": [0.5, 0.9], "arousal": [0.1, 0.5]},
    "neutral": {"valence": [0.4, 0.6], "arousal": [0.4, 0.6]} # Added neutral
}

def map_va_to_emotion(valence, arousal, mapping=emotion_mapping_vad):
    """Map valence and arousal values to emotion labels based on defined ranges."""
    # Normalize VAD values from [-1, 1] (model output) to [0, 1] for mapping
    valence_norm = (valence + 1.0) / 2.0
    arousal_norm = (arousal + 1.0) / 2.0

    matched_emotions = []
    for emotion, ranges in mapping.items():
        v_range = ranges.get("valence", (0.0, 1.0))
        a_range = ranges.get("arousal", (0.0, 1.0))
        if v_range[0] <= valence_norm <= v_range[1] and a_range[0] <= arousal_norm <= a_range[1]:
            matched_emotions.append(emotion)

    if not matched_emotions:
        min_dist = float('inf')
        closest_emotion = "neutral" # Default to neutral
        for emotion, ranges in mapping.items():
            v_center = (ranges.get("valence", (0.0, 1.0))[0] + ranges.get("valence", (0.0, 1.0))[1]) / 2
            a_center = (ranges.get("arousal", (0.0, 1.0))[0] + ranges.get("arousal", (0.0, 1.0))[1]) / 2
            distance = np.sqrt((valence_norm - v_center)**2 + (arousal_norm - a_center)**2)
            if distance < min_dist:
                min_dist = distance
                closest_emotion = emotion
        matched_emotions = [closest_emotion]

    # Return the first matched emotion (or closest)
    return matched_emotions[0] if matched_emotions else "neutral"

# Map overall VAD to a discrete label
overall_discrete_emotion = map_va_to_emotion(overall_valence, overall_arousal)
print(f"Overall Discrete Emotion Estimate: {overall_discrete_emotion}")


# === Chunk audio and run chunk-level emotion analysis ===
print(f"⏱️ Analyzing audio in {chunk_duration_sec}s chunks...")
chunk_size = int(chunk_duration_sec * sr)
chunks = [waveform[i:i + chunk_size] for i in range(0, len(waveform), chunk_size)]

with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    # Add new columns for overall VAD
    writer.writerow([
        "Start Time (s)",
        "ChunkValence", "ChunkArousal", "ChunkDominance", "ChunkDiscreteEmotion",
        "OverallValence", "OverallArousal", "OverallDominance", "OverallDiscreteEmotion"
    ])

    for i, chunk in enumerate(chunks):
        # Skip last chunk if too short (might skew results)
        if len(chunk) < chunk_size * 0.5: # Allow slightly shorter last chunk
            continue

        # Calculate chunk VAD
        chunk_result = emotion_classifier(chunk, sr)
        chunk_valence = chunk_result.get("valence", 0.0)
        chunk_arousal = chunk_result.get("arousal", 0.0)
        # Estimate chunk dominance
        chunk_dominance = np.tanh((chunk_valence + chunk_arousal) / 2)
        # Map chunk VAD to discrete label
        chunk_discrete_emotion = map_va_to_emotion(chunk_valence, chunk_arousal)

        start_time = round(i * chunk_duration_sec, 2)
        writer.writerow([
            start_time,
            round(chunk_valence, 4),
            round(chunk_arousal, 4),
            round(chunk_dominance, 4),
            chunk_discrete_emotion, # Add chunk discrete emotion
            round(overall_valence, 4), # Add overall values to each row
            round(overall_arousal, 4),
            round(overall_dominance, 4),
            overall_discrete_emotion # Add overall discrete emotion
        ])

print(f"✅ Chunk/Overall VAD and Discrete Emotion timeline saved to {output_csv}")
