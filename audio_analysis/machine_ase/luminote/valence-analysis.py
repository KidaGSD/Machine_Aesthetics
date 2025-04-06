import sys, os, csv
import librosa
import numpy as np
import torch
from audio_classifiers.emotion_classifier import EmotionClassifier

# === Fix path if needed
sys.path.append(os.path.dirname(__file__))

# === CLI Argument (audio path)
if len(sys.argv) > 1:
    audio_path = sys.argv[1]
else:
    raise ValueError("❌ Please provide an audio file path as an argument.")

# === Config
output_csv = "valence_arousal_timeline.csv"
sampling_rate = 44100
chunk_duration_sec = 10

# === Load audio
print("🔊 Loading audio...")
waveform, sr = librosa.load(audio_path, sr=sampling_rate)

# === Set up emotion model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
emotion_classifier = EmotionClassifier(device)

# === Chunking + emotion extraction
chunk_size = int(chunk_duration_sec * sr)
chunks = [waveform[i:i + chunk_size] for i in range(0, len(waveform), chunk_size)]

with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Start Time (s)", "Valence", "Arousal"])

    for i, chunk in enumerate(chunks):
        if len(chunk) < chunk_size:
            continue
        result = emotion_classifier(chunk, sr)
        valence = result.get("valence", 0.0)
        arousal = result.get("arousal", 0.0)
        start_time = i * chunk_duration_sec
        writer.writerow([start_time, round(valence, 4), round(arousal, 4)])

print(f"✅ Valence + Arousal timeline saved to {output_csv}")
