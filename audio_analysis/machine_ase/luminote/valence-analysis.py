import os
import csv
import librosa
import numpy as np
import torch
from pydub import AudioSegment
from audio_classifiers.emotion_classifier import EmotionClassifier

# === 🔊 Set your audio file path here ===
input_path = os.path.join(os.path.dirname(__file__), "audio", "sudden-angry.wav")

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
output_csv = os.path.join(os.path.dirname(__file__), "valence_arousal_timeline-angry.csv")
sampling_rate = 44100
chunk_duration_sec = 0.5

# === Load audio ===
print(f"🔊 Loading audio from: {audio_path}")
waveform, sr = librosa.load(audio_path, sr=sampling_rate)

# === Set up emotion classifier ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
emotion_classifier = EmotionClassifier(device)

# === Chunk audio and run emotion analysis ===
chunk_size = int(chunk_duration_sec * sr)
chunks = [waveform[i:i + chunk_size] for i in range(0, len(waveform), chunk_size)]

with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Start Time (s)", "Valence", "Arousal", "Dominance"])

    for i, chunk in enumerate(chunks):
        if len(chunk) < chunk_size:
            continue
        result = emotion_classifier(chunk, sr)
        valence = result.get("valence", 0.0)
        arousal = result.get("arousal", 0.0)

        # === Estimate dominance from valence + arousal ===
        dominance = np.tanh((valence + arousal) / 2)

        start_time = round(i * chunk_duration_sec, 2)
        writer.writerow([
            start_time,
            round(valence, 4),
            round(arousal, 4),
            round(dominance, 4)
        ])

print(f"✅ Valence + Arousal + Dominance timeline saved to {output_csv}")
