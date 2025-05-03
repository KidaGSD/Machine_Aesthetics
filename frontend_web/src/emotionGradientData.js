// emotionGradientData.js — Interpolated from time-based emotion keyframes

// 🔸 Define key emotional states at specific timepoints (in seconds)
// These are like checkpoints along a timeline (e.g., from an audio analysis)
const emotionKeyframes = [
    { time: 0, valence: 0.2, arousal: 0.8 },   // High-energy positive at start
    { time: 2, valence: -0.1, arousal: 0.6 },  // Mildly negative, slightly calmer
    { time: 6, valence: 0.3, arousal: 0.4 },   // Calmer and slightly positive
    { time: 10, valence: 0.0, arousal: 0.7 },  // Neutral but emotionally alert
  ];
  
  // 🔸 Determine total duration of the emotional timeline
  const totalTime = emotionKeyframes[emotionKeyframes.length - 1].time;
  
  // 🔸 Generate 100 emotion values evenly spaced over the timeline (0 to totalTime)
  // This provides one valence/arousal pair per vertical mesh segment (or frame)
  const emotionGradientData = Array.from({ length: 100 }, (_, i) => {
    // Normalize i (0–99) into a time value between 0 and totalTime
    const t = (i / 99) * totalTime;
  
    // 🔸 Find the two keyframes that surround this time `t`
    const idx = emotionKeyframes.findIndex((e, j) =>
      t >= e.time && t < (emotionKeyframes[j + 1]?.time ?? Infinity)
    );
    const start = emotionKeyframes[idx];
    const end = emotionKeyframes[idx + 1] ?? start; // fallback if at last keyframe
  
    // 🔸 Compute interpolation ratio between start and end keyframes
    const span = end.time - start.time || 1;
    const localT = (t - start.time) / span;
  
    // 🔸 Linearly interpolate valence and arousal based on localT
    const valence = start.valence * (1 - localT) + end.valence * localT;
    const arousal = start.arousal * (1 - localT) + end.arousal * localT;
  
    // 🔸 Return a cleaned and rounded emotional value pair for this time slice
    return {
      valence: parseFloat(valence.toFixed(3)),
      arousal: parseFloat(arousal.toFixed(3)),
    };
  });
  
  // 🔸 Export the full timeline of interpolated emotion values
  export default emotionGradientData;
  