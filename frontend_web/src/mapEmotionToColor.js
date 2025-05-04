
import * as THREE from 'three';

/**
 * Generate a color variation based on baseColor,
 * adjusted using valence and arousal values.
 * 
 * @param {number} valence - from -1 (negative) to 1 (positive)
 * @param {number} arousal - from 0 (low) to 1 (high)
 * @param {THREE.Color} baseColor - the base hue to vary
 * @returns {THREE.Color}
 */
export function mapEmotionToColor(valence, arousal, baseColor) {
  const hsl = {};
  baseColor.getHSL(hsl);

  // Shift lightness based on arousal
  const lightness = Math.max(0, Math.min(1, hsl.l + (arousal - 0.5) * 0.4));

  // Optionally shift saturation based on valence
  const saturation = Math.max(0, Math.min(1, hsl.s + valence * 0.3));

  const result = new THREE.Color();
  result.setHSL(hsl.h, saturation, lightness);
  return result;
}
