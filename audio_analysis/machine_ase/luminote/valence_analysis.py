import os, csv
import librosa
import torch
from pydub import AudioSegment
from audio_classifiers.emotion_classifier import EmotionClassifier

def process_audio(input_path, output_dir):
    # Convert MP3 to WAV if needed
    if input_path.lower().endswith(".mp3"):
        print("🎧 Converting .mp3 to .wav...")
        wav_path = input_path.replace(".mp3", ".wav")
        audio = AudioSegment.from_mp3(input_path)
        audio.export(wav_path, format="wav")
        input_path = wav_path

    output_csv = os.path.join(output_dir, "valence_arousal_output.csv")
    print(f"🔊 Loading audio from: {input_path}")
    waveform, sr = librosa.load(input_path, sr=44100)

    chunk_size = int(sr)
    chunks = [waveform[i:i + chunk_size] for i in range(0, len(waveform), chunk_size)]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    emotion_classifier = EmotionClassifier(device)

    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Start Time (s)", "Valence", "Arousal", "Dominance"])
        for i, chunk in enumerate(chunks):
            if len(chunk) < chunk_size:
                continue
            result = emotion_classifier(chunk, sr)
            writer.writerow([
                i,
                round(result.get("valence", 0.0), 4),
                round(result.get("arousal", 0.0), 4),
                round(result.get("dominance", 0.0), 4),
            ])

    print(f"✅ CSV saved at: {output_csv}")
    return output_csv
