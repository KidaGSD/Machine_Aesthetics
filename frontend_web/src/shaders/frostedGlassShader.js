import * as THREE from 'three';

export const frostedGlassShader = new THREE.ShaderMaterial({
  uniforms: {
    uColorTop: { value: new THREE.Color(0xf8f3e6) },       // soft off-white
    uColorMiddle: { value: new THREE.Color(0xf1e9dc) },    // warmer beige
    uColorBottom: { value: new THREE.Color(0xe9dfd0) },    // deeper warm
    uFresnelColor: { value: new THREE.Color(1.0, 0.95, 0.85) }, // warm edge highlight
    uFresnelPower: { value: 3.0 },
    uOpacity: { value: 0.6 },
    uThicknessFogColor: { value: new THREE.Color(1.0, 0.94, 0.82) },  // warm fog tone
    uFogStrength: { value: 0.8 },
  },

  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vViewDir;
    varying float vY;

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      vViewDir = normalize(-mvPosition.xyz);
      vY = position.y;
      gl_Position = projectionMatrix * mvPosition;
    }
  `,

  fragmentShader: `
    uniform vec3 uColorTop;
    uniform vec3 uColorMiddle;
    uniform vec3 uColorBottom;
    uniform vec3 uFresnelColor;
    uniform vec3 uThicknessFogColor;
    uniform float uFresnelPower;
    uniform float uOpacity;
    uniform float uFogStrength;

    varying vec3 vNormal;
    varying vec3 vViewDir;
    varying float vY;

    void main() {
      float fresnel = pow(1.0 - dot(vNormal, vViewDir), uFresnelPower);

      float t = clamp((vY + 1.0) / 2.0, 0.0, 1.0);

      vec3 baseColor;
      if (t < 0.5) {
        float localT = t / 0.5;
        baseColor = mix(uColorBottom, uColorMiddle, smoothstep(0.0, 1.0, localT));
      } else {
        float localT = (t - 0.5) / 0.5;
        baseColor = mix(uColorMiddle, uColorTop, smoothstep(0.0, 1.0, localT));
      }

      // Simulate thickness fog
      float depthFactor = 1.0 - abs(dot(vNormal, vViewDir));
      vec3 foggedColor = mix(baseColor, uThicknessFogColor, depthFactor * uFogStrength);

      // Simulate internal lamp glow
      float centerGlow = 1.0 - length(vViewDir);
      vec3 glowColor = vec3(1.0, 0.9, 0.7);  // soft yellow tone
      vec3 lightingEffect = mix(foggedColor, glowColor, centerGlow * 0.2);

      // Fresnel highlight
      vec3 finalColor = mix(lightingEffect, uFresnelColor, fresnel * 0.3);

      gl_FragColor = vec4(finalColor, uOpacity + fresnel * 0.15 + centerGlow * 0.1);
    }
  `,

  transparent: true,
  depthWrite: false,
});
