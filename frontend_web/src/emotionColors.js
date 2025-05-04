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

export default emotionColors;
