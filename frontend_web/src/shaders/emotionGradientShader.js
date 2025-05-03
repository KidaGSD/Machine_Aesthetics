// emotionGradientShader.js
import * as THREE from 'three';

export const emotionGradientShader = new THREE.ShaderMaterial({
  uniforms: {
    baseHue: { value: 0.0 }, // passed as float (0 to 1), e.g. red = 0.0
  },
  vertexShader: `
    attribute float valence;
    attribute float arousal;
    varying float vValence;
    varying float vArousal;

    void main() {
      vValence = valence;
      vArousal = arousal;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    varying float vValence;
    varying float vArousal;
    uniform float baseHue;

    vec3 hsl2rgb(vec3 hsl) {
      float c = (1.0 - abs(2.0 * hsl.z - 1.0)) * hsl.y;
      float x = c * (1.0 - abs(mod(hsl.x * 6.0, 2.0) - 1.0));
      float m = hsl.z - c / 2.0;
      vec3 rgb;
      if (hsl.x < 1.0/6.0) rgb = vec3(c, x, 0.0);
      else if (hsl.x < 2.0/6.0) rgb = vec3(x, c, 0.0);
      else if (hsl.x < 3.0/6.0) rgb = vec3(0.0, c, x);
      else if (hsl.x < 4.0/6.0) rgb = vec3(0.0, x, c);
      else if (hsl.x < 5.0/6.0) rgb = vec3(x, 0.0, c);
      else rgb = vec3(c, 0.0, x);
      return rgb + vec3(m);
    }

    void main() {
      float lightness = clamp(0.4 + vArousal * 0.5, 0.0, 1.0);
      float saturation = clamp(0.6 + vValence * 0.4, 0.0, 1.0);
      vec3 color = hsl2rgb(vec3(baseHue, saturation, lightness));
      gl_FragColor = vec4(color, 1.0);
    }
  `,
  vertexColors: false,
});
