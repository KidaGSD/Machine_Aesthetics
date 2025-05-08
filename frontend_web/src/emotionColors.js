// emotionColors.js 
// here we define the basic color of each emotion, which are determined by the base shape in mesh_deformation.js

import * as THREE from 'three';

const emotionColors = {
  joy: new THREE.Color('#FFD700'),       // bright yellow
  sadness: new THREE.Color('#1E90FF'),   // deep sky blue
  anger: new THREE.Color('#FF4500'),     // orange red
  fear: new THREE.Color('#800080'),      // purple
  surprise: new THREE.Color('#FFB12A'),  // orange
  neutral: new THREE.Color('#00CED1'),   // blue
  disgust: new THREE.Color('#556B2F'),   // dark olive green
};

// Helper function to get an emotion color by name
export const getEmotionColor = (emotion) => {
  // Convert to lowercase for consistent matching
  const normalizedEmotion = emotion.toLowerCase();
  
  // Handle common emotion aliases
  const emotionMap = {
    'angry': 'anger',
    'fearful': 'fear',
    'happy': 'joy',
    'sad': 'sadness',
    'disgusted': 'disgust',
    'surprised': 'surprise',
    'serene': 'neutral'
  };
  
  // Get the standardized emotion name
  const standardEmotion = emotionMap[normalizedEmotion] || normalizedEmotion;
  
  // Return the color or a default if not found
  return emotionColors[standardEmotion] || emotionColors.neutral;
};

export default emotionColors;
