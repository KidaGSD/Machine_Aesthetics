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
<<<<<<< Updated upstream
      float lightness = clamp(0.4 + vArousal * 0.5, 0.0, 1.0);
      float saturation = clamp(0.6 + vValence * 0.4, 0.0, 1.0);
      vec3 color = hsl2rgb(vec3(baseHue, saturation, lightness));
      gl_FragColor = vec4(color, 1.0);
=======
      // --- Simplified Color Blending --- 
      // Blend between the two provided RGB colors based on vertical position
      float colorBlendFactor = smoothstep(0.1, 0.9, vVerticalBlend); // Smooth blending
      vec3 baseColor = mix(colorTop, colorBottom, colorBlendFactor);
      
      // Optionally, subtly adjust lightness based on valence
      baseColor *= (1.0 + vValence * 0.1);
      
      // Normal calculation
      vec3 normal = normalize(vNormal);
      vec3 viewDir = normalize(vViewPosition);
      
      // Apply normal mapping if enabled
      if (useTexture > 0.5) { 
        // Use tiled UVs
        vec2 tiledUv = vUv * textureTiling;
        
        // Sample normal maps
        vec3 normalFromMap1 = sampleNormalSmooth(normalMap, tiledUv, textureDetail);
        vec3 normalFromMap2 = sampleNormalSmooth(normalMap2, tiledUv, textureDetail);
        
        // Blend normals based on vertical position (with some sharpness)
        float normalBlendFactor = smoothstep(0.2, 0.8, vVerticalBlend);
        vec3 blendedNormalMap = normalize(mix(normalFromMap1, normalFromMap2, normalBlendFactor));
        
        // Apply normal scale
        blendedNormalMap.xy *= normalScale;
        blendedNormalMap = normalize(blendedNormalMap);
        
        // Create TBN matrix
        vec3 q0 = dFdx(vViewPosition);
        vec3 q1 = dFdy(vViewPosition);
        vec2 st0 = dFdx(vUv);
        vec2 st1 = dFdy(vUv);
        
        vec3 N = normalize(vNormal);
        vec3 T = normalize(q0 * st1.t - q1 * st0.t);
        vec3 B = -normalize(cross(N, T));
        mat3 TBN = mat3(T, B, N);
        
        // Apply normal map
        normal = normalize(TBN * blendedNormalMap);
      }
      
      // Calculate lighting
      vec3 litColor = calculateLighting(baseColor, normal, viewDir);
      
      // Output final color
      gl_FragColor = vec4(litColor, 1);
>>>>>>> Stashed changes
    }
  `,
  vertexColors: false,
});
