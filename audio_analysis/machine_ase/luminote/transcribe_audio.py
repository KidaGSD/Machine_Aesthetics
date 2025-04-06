import os
import sys
import subprocess
import whisper

# === Get audio file path from command line argument
if len(sys.argv) > 1:
    audio_path = sys.argv[1]
else:
    raise ValueError("❌ Please provide the audio file path as a command-line argument.")

# === Step 1: Run Demucs to separate vocals
print("🎧 Running Demucs to separate vocals...")
demucs_command = ["demucs", audio_path]
subprocess.run(demucs_command)

# === Step 2: Locate the Demucs output (vocals)
filename = os.path.basename(audio_path).replace(".mp3", "").replace(".wav", "")
vocals_path = f"separated/htdemucs/{filename}/vocals.wav"

if not os.path.exists(vocals_path):
    raise FileNotFoundError(f"❌ Could not find vocals at {vocals_path}")

# === Step 3: Transcribe with Whisper
print("🤖 Loading Whisper model...")
model = whisper.load_model("medium")

print(f"📝 Transcribing vocals from: {vocals_path}")
result = model.transcribe(vocals_path, language="en")

# === Step 4: Save transcript
transcript = result["text"]
print("\n📝 Transcript:\n", transcript)

with open("transcript.txt", "w") as f:
    f.write(transcript)

print("✅ Transcript saved to transcript.txt")
