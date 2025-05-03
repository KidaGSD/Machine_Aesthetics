import os
import csv
import numpy as np

# === Settings ===
input_csv = os.path.join(os.path.dirname(__file__), "valence_arousal_timeline-sobbing.csv")
output_csv = os.path.join(os.path.dirname(__file__), "filtered_valence_arousal_20steps.csv")

target_steps = 20  # How many total steps you want
smoothing_window = 5  # How much smoothing: larger = smoother

# === Load the CSV ===
valence = []
arousal = []

with open(input_csv, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            valence.append(float(row["Valence"]))
            arousal.append(float(row["Arousal"]))
        except:
            continue

# === Smooth the curves ===
def moving_average(arr, window_size):
    return np.convolve(arr, np.ones(window_size)/window_size, mode='same')

valence_smooth = moving_average(valence, smoothing_window)
arousal_smooth = moving_average(arousal, smoothing_window)

# === Resample 20 evenly spaced points ===
total_points = len(valence_smooth)
sample_indices = np.linspace(0, total_points - 1, target_steps).astype(int)

final_valence = [valence_smooth[i] for i in sample_indices]
final_arousal = [arousal_smooth[i] for i in sample_indices]

# === Save cleaned data to CSV ===
with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Start Time (s)", "Valence", "Arousal"])
    for idx, (v, a) in enumerate(zip(final_valence, final_arousal)):
        start_time = round(idx * 0.5, 2)  # dummy timing
        writer.writerow([start_time, round(v, 4), round(a, 4)])

print(f"✅ Smooth interpolated dataset saved to {output_csv}")
