import * as THREE from 'three';

export const frostedGlassShader = new THREE.ShaderMaterial({
  uniforms: {
    uColorTop: { value: new THREE.Color(0xe3dfe0) },
    uColorMiddle: { value: new THREE.Color(0xbab5c3) },
    uColorBottom: { value: new THREE.Color(0xCED6DD) },
    uFresnelColor: { value: new THREE.Color(0xffffff) },
    uFresnelPower: { value: 4.5 },
    uOpacity: { value: 0.5 },
    uThicknessFogColor: { value: new THREE.Color(0xdde2ea) },  // inner fog color
    uFogStrength: { value: 0.6 },                              // how strong the fog appears
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

      // 🔮 Simulate depth fog based on angle (thicker when viewed from side)
      float depthFactor = 1.0 - abs(dot(vNormal, vViewDir));
      vec3 foggedColor = mix(baseColor, uThicknessFogColor, depthFactor * uFogStrength);

      // ✨ Fresnel highlight
      vec3 finalColor = mix(foggedColor, uFresnelColor, fresnel);

      gl_FragColor = vec4(finalColor, uOpacity + fresnel * 0.2);
    }
  `,
  transparent: true,
  depthWrite: false,
});
