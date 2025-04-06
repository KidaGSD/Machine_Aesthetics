import subprocess

# === Set your audio file path once here ===
audio_file = "audio/ccnews.mp3"  # 👈 Change this once!

# === STEP 1: Transcribe audio (writes transcript.txt)
print("🎙️ Running transcription...")
subprocess.run(["python", "transcribe_audio.py", audio_file])

# === STEP 2: Analyze emotion using Claude API (reads transcript.txt, writes emotion_label.csv)
print("🧠 Running Claude emotion summary...")
subprocess.run(["python", "text-to-emotion-analysis.py"])

# === STEP 3: Run valence analysis (writes valence_arousal_timeline.csv)
print("📈 Running valence/arousal analysis...")
subprocess.run(["python", "valence-analysis.py", audio_file])

print("✅ All steps complete!")

if __name__ == "__main__":
    import sys
    audio_path = sys.argv[1]
    # Your existing code using audio_path
