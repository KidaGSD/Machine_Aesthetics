// emotionColors.js 
// Define the basic color of each emotion, which are determined by the base shape in mesh_deformation.js

import * as THREE from 'three';

// Enhanced emotion color palette with better color theory mapping
// - Using more saturated and emotionally resonant colors
// - Providing variants for different cases/spellings
const emotionColors = {
  // Primary emotion colors
  joy: new THREE.Color('#FFD700'),          // bright gold yellow
  sadness: new THREE.Color('#1E78AD'),      // deeper, richer blue
  anger: new THREE.Color('#E53935'),        // vibrant red
  fear: new THREE.Color('#8E24AA'),         // deep purple
  surprise: new THREE.Color('#FF9E22'),     // vibrant orange
  neutral: new THREE.Color('#00B5BA'),      // turquoise
  disgust: new THREE.Color('#558B2F'),      // olive green
  
  // Variants for different spellings or intensities
  sad: new THREE.Color('#1E78AD'),          // same as sadness
  angry: new THREE.Color('#E53935'),        // same as anger
  surprised: new THREE.Color('#FF9E22'),    // same as surprise
  fearful: new THREE.Color('#8E24AA'),      // same as fear
  disgusted: new THREE.Color('#558B2F'),    // same as disgust
  
  // Additional emotional states often detected
  serene: new THREE.Color('#00B5BA'),       // similar to neutral with slight adjustment
  calm: new THREE.Color('#00ACC1'),         // light blue-green
  peaceful: new THREE.Color('#4FC3F7'),     // light blue
  excited: new THREE.Color('#FFEB3B'),      // bright yellow
  happy: new THREE.Color('#FFC107'),        // amber-gold
  anxious: new THREE.Color('#9575CD'),      // lighter purple
  nervous: new THREE.Color('#7986CB'),      // blue-purple
  relaxed: new THREE.Color('#4DD0E1'),      // light teal
  tense: new THREE.Color('#D81B60'),        // raspberry
  annoyed: new THREE.Color('#F4511E'),      // burnt orange
  
  // Default fallback
  default: new THREE.Color('#BDBDBD'),      // neutral gray
};

// Utility function to get an emotion color with fallbacks for similar emotions
export function getEmotionColor(emotion) {
  // Normalize the emotion name
  const normalizedEmotion = (emotion || "").toLowerCase().trim();
  
  // Direct match
  if (emotionColors[normalizedEmotion]) {
    return emotionColors[normalizedEmotion];
  }
  
  // Check similar emotions
  const similarMap = {
    // Joy family
    "happy": "joy",
    "excited": "joy",
    "delighted": "joy",
    "pleased": "joy",
    "content": "joy",
    
    // Sadness family
    "sad": "sadness",
    "depressed": "sadness",
    "melancholy": "sadness",
    "unhappy": "sadness",
    "gloomy": "sadness",
    
    // Anger family
    "angry": "anger",
    "furious": "anger",
    "annoyed": "anger",
    "irritated": "anger",
    "enraged": "anger",
    
    // Fear family
    "scared": "fear",
    "fearful": "fear",
    "terrified": "fear",
    "anxious": "fear",
    "nervous": "fear",
    
    // Surprise family
    "surprised": "surprise",
    "amazed": "surprise",
    "astonished": "surprise",
    "shocked": "surprise",
    
    // Neutral family
    "calm": "neutral",
    "peaceful": "neutral",
    "relaxed": "neutral",
    "serene": "neutral",
    
    // Disgust family
    "disgusted": "disgust",
    "revolted": "disgust",
    "repulsed": "disgust"
  };
  
  // Check for similar emotion mapping
  if (similarMap[normalizedEmotion]) {
    return emotionColors[similarMap[normalizedEmotion]];
  }
  
  // Return default as fallback
  return emotionColors.default;
}

export default emotionColors;
