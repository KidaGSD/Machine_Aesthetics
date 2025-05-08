// emotionGradientShader.js
import * as THREE from 'three';

export const emotionGradientShader = new THREE.ShaderMaterial({
  uniforms: {
    baseHue: { value: 0.0 }, // base hue adjustment
    colorTop: { value: new THREE.Color(0x1E90FF) }, // default blue
    colorBottom: { value: new THREE.Color(0xFFD700) }, // default gold
    useTexture: { value: 1.0 }, // toggle for using textures
    textureTiling: { value: 2.0 }, // how many times to tile the texture
    normalMap: { value: null }, // top normal map
    normalMap2: { value: null }, // bottom normal map
    displacementMap: { value: null }, // top displacement map
    displacementMap2: { value: null }, // bottom displacement map
    normalScale: { value: 0.5 }, // how strong the normal mapping is
    displacementScale: { value: 2.0 }, // how strong the displacement is
    displacementBias: { value: 0.0 }, // bias for displacement
    textureDetail: { value: 0.7 }, // texture detail/roughness control
    revealProgress: { value: 1.0 }, // for reveal animation (0-1)
    time: { value: 0.0 } // for subtle animations
  },
  vertexShader: `
    attribute float valence;
    attribute float arousal;
    varying float vValence;
    varying float vArousal;
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying float vVerticalBlend;

    void main() {
      vValence = valence;
      vArousal = arousal;
      vUv = uv;
      vNormal = normal;
      
      // Calculate vertical position for color blending
      vVerticalBlend = uv.y; // Use UV's y component for vertical blending
      
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewPosition = -mvPosition.xyz; // For lighting calculations
      
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying float vValence;
    varying float vArousal;
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying float vVerticalBlend;
    
    uniform float baseHue;
    uniform vec3 colorTop;
    uniform vec3 colorBottom;
    uniform float useTexture;
    uniform float textureTiling;
    uniform sampler2D normalMap;
    uniform sampler2D normalMap2;
    uniform float normalScale;
    uniform float textureDetail;
    uniform float revealProgress;
    uniform float time;
    
    // Function to sample normal map with smoothstep
    vec3 sampleNormalSmooth(sampler2D map, vec2 uv, float detail) {
      vec4 normalSample = texture2D(map, uv);
      vec3 normal = normalSample.xyz * 2.0 - 1.0;
      
      // Adjust normal strength based on detail parameter
      normal.xy *= mix(0.3, 1.0, detail);
      return normalize(normal);
    }
    
    // Phong lighting calculation
    vec3 calculateLighting(vec3 baseColor, vec3 normal, vec3 viewDir) {
      // Main directional light from above and behind
      vec3 lightDir = normalize(vec3(0.5, 1.0, 0.5));
      float diff = max(dot(normal, lightDir), 0.0);
      
      // Ambient light
      float ambientStrength = 0.4;
      vec3 ambient = ambientStrength * vec3(1.0);
      
      // Diffuse
      vec3 diffuse = diff * vec3(1.0);
      
      // Specular highlights
      float specularStrength = 0.3 * (1.0 + vValence * 0.2); // More specular for positive emotions
      vec3 reflectDir = reflect(-lightDir, normal);
      float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
      vec3 specular = specularStrength * spec * vec3(1.0, 1.0, 1.0);
      
      // Calculate rim lighting (edge highlight)
      float rimStrength = 0.3;
      float rimFactor = 1.0 - max(dot(viewDir, normal), 0.0);
      rimFactor = smoothstep(0.5, 1.0, rimFactor);
      vec3 rim = rimStrength * rimFactor * vec3(1.0);
      
      // Combine all lighting components
      return (ambient + diffuse) * baseColor + specular + rim * baseColor;
    }

    void main() {
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
    }
  `,
  vertexColors: false,
  side: THREE.DoubleSide,
  // Add necessary shader features
  lights: false,
  transparent: false,
});
