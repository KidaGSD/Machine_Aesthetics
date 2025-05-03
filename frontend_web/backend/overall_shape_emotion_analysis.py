# Required: pip install git+https://github.com/openai/whisper.git

import os
import numpy as np
if not hasattr(np, 'complex'):
    np.complex = complex  # for librosa compatibility

import librosa
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from transformers import pipeline
from pydub import AudioSegment
import subprocess
import whisper

def run_analysis(audio_path):
    print("🎬 Converting to WAV if needed...")
    if audio_path.lower().endswith(".mp3"):
        wav_path = audio_path.replace(".mp3", ".wav")
        audio = AudioSegment.from_mp3(audio_path)
        audio.export(wav_path, format="wav")
        audio_path = wav_path
    elif audio_path.lower().endswith(".mp4"):
        wav_path = audio_path.replace(".mp4", ".wav")
        command = f"ffmpeg -i \"{audio_path}\" -vn -acodec pcm_s16le -ar 44100 -ac 2 \"{wav_path}\""
        subprocess.call(command, shell=True)
        audio_path = wav_path

    print("🗣️ Transcribing audio...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=False)
    transcript_segments = [{
        "start": seg['start'],
        "end": seg['end'],
        "text": seg['text'].strip()
    } for seg in result['segments']]

    if not transcript_segments:
        print("❌ No transcription results. Aborting.")
        return

    y, sr = librosa.load(audio_path)
    hop_length = 512

    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    mfcc1 = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length, n_mfcc=1)[0]

    min_length = min(len(rms), len(zcr), len(centroid), len(mfcc1))
    rms, zcr, centroid, mfcc1 = rms[:min_length], zcr[:min_length], centroid[:min_length], mfcc1[:min_length]

    classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=False)
    emotion_vad_map = {
        'joy': (0.9, 0.8), 'sadness': (-0.7, 0.3), 'anger': (-0.6, 0.9),
        'disgust': (-0.8, 0.7), 'fear': (-0.6, 0.8), 'surprise': (0.5, 0.9), 'neutral': (0.0, 0.0)
    }

    def analyze_emotion_combined(text, audio_slice, sr):
        try:
            result = classifier(text)[0]
            label = result['label'].lower()
            valence_text, arousal_text = emotion_vad_map.get(label, (0.0, 0.0))
        except:
            label, valence_text, arousal_text = "neutral", 0.0, 0.0

        if len(audio_slice) > 0:
            rms = librosa.feature.rms(y=audio_slice)[0].mean()
            zcr = librosa.feature.zero_crossing_rate(y=audio_slice)[0].mean()
            centroid = librosa.feature.spectral_centroid(y=audio_slice, sr=sr)[0].mean()
            mfcc = librosa.feature.mfcc(y=audio_slice, sr=sr, n_mfcc=1)[0].mean()
        else:
            rms, zcr, centroid, mfcc = 0, 0, 0, 0

        valence_audio = np.clip((centroid / 5000.0) + (zcr * 2) - 1, -1.0, 1.0)
        arousal_audio = np.clip((rms * 10) + (mfcc / 200.0), -1.0, 1.0)
        return {
            "emotion": label,
            "valence": round((valence_text + valence_audio) / 2, 4),
            "arousal": round((arousal_text + arousal_audio) / 2, 4)
        }

    # Analyze each segment
    segment_summaries = []
    for seg in transcript_segments:
        start_sample = int(seg['start'] * sr)
        end_sample = int(seg['end'] * sr)
        audio_slice = y[start_sample:end_sample]
        emo = analyze_emotion_combined(seg['text'], audio_slice, sr)
        segment_summaries.append({**seg, **emo, "duration": seg["end"] - seg["start"]})

    df_summary = pd.DataFrame(segment_summaries)
    base_path = os.path.join(os.path.dirname(__file__), "../public/data")
    os.makedirs(base_path, exist_ok=True)

    if df_summary.empty:
        print("❌ No audio analysis results. Skipping CSV export.")
        return

    # === Grouped Emotion Summary
    df_grouped = df_summary.groupby('emotion').agg({
        'valence': 'mean',
        'arousal': 'mean',
        'duration': 'sum'
    }).reset_index()

    top2 = df_grouped.sort_values(by='duration', ascending=False).head(2)
    top2.to_csv(os.path.join(base_path, "top2_emotion_summary.csv"), index=False)

    # === Full Segment Detail
    df_summary.to_csv(os.path.join(base_path, "summary_per_segment.csv"), index=False)

    # === Smoothed Arousal Track (100 points)
    arousal_full = df_summary['arousal'].to_numpy()

    if len(arousal_full) > 1:
        arousal_interp = np.interp(
            np.linspace(0, len(arousal_full) - 1, 100),
            np.arange(len(arousal_full)),
            arousal_full
        )
    else:
        fallback_value = float(arousal_full[0]) if len(arousal_full) == 1 else 0.0
        arousal_interp = np.full(100, fallback_value)

    pd.DataFrame({"arousal": arousal_interp}).to_csv(os.path.join(base_path, "arousal_100.csv"), index=False)

    print("✅ Emotion analysis complete.")
