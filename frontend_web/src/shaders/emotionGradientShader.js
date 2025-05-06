// emotionGradientShader.js
import * as THREE from 'three';

export const emotionGradientShader = new THREE.ShaderMaterial({
  uniforms: {
    baseHue: { value: 0.0 }, // Bottom emotion base hue
    topHue: { value: 0.3 }, // Top emotion base hue
    colorTop: { value: new THREE.Color(0xffffff) }, // Use full RGB for top color
    colorBottom: { value: new THREE.Color(0x0000ff) }, // Use full RGB for bottom color
    displacementMap: { value: null }, // displacement texture
    displacementScale: { value: 1.5 }, // Adjusted for visibility
    normalMap: { value: null }, // normal map texture
    normalScale: { value: new THREE.Vector2(1.0, 1.0) }, // normal map intensity
    useTexture: { value: 1.0 }, // 0.0 for no texture, 1.0 for full texture
    revealProgress: { value: 0.0 }, 
    // Second texture for blending
    displacementMap2: { value: null },
    normalMap2: { value: null },
    textureDetail: { value: 0.6 }, // Adjusted detail level
    textureTiling: { value: 2.0 }, // Control texture repetition
    textureContrast: { value: 1.4 }, // Extra control for texture visibility
    blendSharpness: { value: 0.8 }, // Sharper blend between textures/colors
    time: { value: 0.0 }, // Uniform for subtle animation effects
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
    varying vec3 vWorldPosition;
    
    uniform float displacementScale;
    uniform sampler2D displacementMap;
    uniform sampler2D displacementMap2;
    uniform float useTexture;
    uniform float revealProgress;
    uniform float textureDetail;
    uniform float textureTiling;
    uniform float textureContrast;
    uniform float time;
    
    // Noise functions (simplified for clarity)
    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
    }
    
    float noise(vec2 p) {
      vec2 i = floor(p);
      vec2 f = fract(p);
      f = f * f * (3.0 - 2.0 * f);
      return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
                 mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
    }
    
    float fbm(vec2 p) {
      float value = 0.0;
      float amplitude = 0.5;
      float frequency = 1.0;
      for (int i = 0; i < 4; i++) {
        value += amplitude * noise(p * frequency);
        amplitude *= 0.5;
        frequency *= 2.0;
      }
      return value;
    }

    // Sample displacement with improved filtering and blending
    float sampleDisplacementSmooth(sampler2D map, vec2 uv, float detail) {
      // Bilinear filtering might be sufficient
      vec4 tex = texture2D(map, uv);
      float height = (tex.r + tex.g + tex.b) / 3.0;
      
      // Enhance contrast
      height = pow(height * textureContrast, 1.0) / textureContrast;
      
      // Mix in high-frequency detail 
      float highFreq = texture2D(map, uv * 2.0).r; // Use red channel for detail
      return mix(height, highFreq, detail * 0.3);
    }

    void main() {
      vValence = valence;
      vArousal = arousal;
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
      
      // Store vertical UV coordinate for blending with noise
      float noiseVal = (fbm(vUv * 8.0 + vec2(time * 0.01)) - 0.25) * 0.1;
      vVerticalBlend = clamp(uv.y + noiseVal, 0.0, 1.0); // Clamp to ensure valid blend factor
      
      // Apply displacement mapping in vertex shader if texture is available
      vec3 transformed = position;
      
      if (useTexture > 0.5) { 
        // Tiled UVs
        vec2 tiledUv = vUv * textureTiling;
        
        // Sample displacement - both textures
        float df1 = sampleDisplacementSmooth(displacementMap, tiledUv, textureDetail);
        float df2 = sampleDisplacementSmooth(displacementMap2, tiledUv, textureDetail);
        
        // Blend displacement based on vertical UV (bottom to top)
        float blendFactor = smoothstep(0.3, 0.7, vVerticalBlend);
        float displacement = mix(df1, df2, blendFactor);
        
        // Offset by 0.5 and apply scaled displacement along normal
        float displStrength = (displacement - 0.5) * displacementScale;
        
        // Apply falloff at extreme edges
        float edgeFalloff = 1.0 - pow(abs(uv.y * 2.0 - 1.0), 3.0);
        displStrength *= edgeFalloff;
        
        transformed += normalize(normal) * displStrength;
      }
      
      // Apply reveal animation
      vec3 finalPosition = transformed;
      vec3 initialPosition = vec3(position.x * 0.1, position.y, position.z * 0.1);
      transformed = mix(initialPosition, finalPosition, revealProgress);
      
      // Transform to world space
      vec4 mvPosition = modelViewMatrix * vec4(transformed, 1.0);
      vViewPosition = -mvPosition.xyz;
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
    varying vec3 vWorldPosition;
    
    uniform vec3 colorTop;
    uniform vec3 colorBottom;
    uniform sampler2D normalMap;
    uniform sampler2D normalMap2;
    uniform vec2 normalScale;
    uniform float useTexture;
    uniform float textureDetail;
    uniform float textureTiling;
    uniform float textureContrast;
    uniform float blendSharpness;
    uniform float time;
    
    // Sample normal map with basic filtering
    vec3 sampleNormalSmooth(sampler2D map, vec2 uv, float detail) {
      vec4 normalSample = texture2D(map, uv);
      return normalSample.xyz * 2.0 - 1.0;
    }
    
    // Function to calculate lighting
    vec3 calculateLighting(vec3 baseColor, vec3 normal, vec3 viewDir) {
      // Key light
      vec3 lightDir1 = normalize(vec3(0.5, 1.0, 0.5));
      vec3 lightColor1 = vec3(1.0, 0.95, 0.9) * 0.8;
      
      // Fill light
      vec3 lightDir2 = normalize(vec3(-0.5, 0.2, -0.4));
      vec3 lightColor2 = vec3(0.7, 0.8, 1.0) * 0.3;
      
      // Diffuse
      float diff1 = max(dot(normal, lightDir1), 0.0);
      float diff2 = max(dot(normal, lightDir2), 0.0);
      
      // Ambient
      float ambient = 0.3;
      
      // Specular
      vec3 reflectDir1 = reflect(-lightDir1, normal);
      float spec1 = pow(max(dot(viewDir, reflectDir1), 0.0), 40.0);
      
      // Rim
      float rimFactor = 1.0 - max(dot(normal, viewDir), 0.0);
      float rim = 0.4 * pow(rimFactor, 2.5);
      vec3 rimColor = mix(baseColor, vec3(1.0), 0.4);
      
      // Combine
      vec3 diffuse = (diff1 * lightColor1 + diff2 * lightColor2) * baseColor;
      vec3 specular = (spec1 * 0.5 * lightColor1);
      
      return baseColor * ambient + diffuse + specular + rim * rimColor;
    }

    void main() {
      // --- Simplified Color Blending --- 
      // Blend between the two provided RGB colors based on vertical position
      float colorBlendFactor = smoothstep(0.1, 0.9, vVerticalBlend); // Smooth blending
      vec3 baseColor = mix(colorBottom, colorTop, colorBlendFactor);
      
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
      gl_FragColor = vec4(litColor, 1.0);
    }
  `,
  lights: false,
  transparent: false,
  extensions: {
    derivatives: true
  }
});
