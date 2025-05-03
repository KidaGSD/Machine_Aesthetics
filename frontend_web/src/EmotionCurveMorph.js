// EmotionCurveMorph.js
import React, { useRef, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const EmotionCurveMorph = ({ emotionCurvesPath, emotionA = "j", emotionB = "s" }) => {
  const lineRef = useRef();
  const [curvePoints, setCurvePoints] = useState([]);

  useEffect(() => {
    if (!emotionCurvesPath) return;

    fetch(`${emotionCurvesPath}?t=${Date.now()}`)
      .then((res) => res.json())
      .then((data) => {
        const rawA = data[emotionA];
        const rawB = data[emotionB];
        if (!rawA || !rawB) return;

        const pointsA = rawA.map(([x, y]) => new THREE.Vector3(x, 0, y));
        const pointsB = rawB.map(([x, y]) => new THREE.Vector3(x, 0, y));
        setCurvePoints([pointsA, pointsB]);
      });
  }, [emotionCurvesPath, emotionA, emotionB]);

  useFrame(({ clock }) => {
    if (!lineRef.current || curvePoints.length < 2) return;

    const t = (Math.sin(clock.elapsedTime * 0.5) + 1) / 2;
    const interpolated = curvePoints[0].map((a, i) => {
      const b = curvePoints[1][i];
      return a.clone().lerp(b, t);
    });

    const geometry = new THREE.BufferGeometry().setFromPoints(interpolated);
    lineRef.current.geometry.dispose();
    lineRef.current.geometry = geometry;
  });

  return (
    <>
      <ambientLight />
      <line ref={lineRef}>
        <bufferGeometry />
        <lineBasicMaterial color="#ffffff" linewidth={2} />
      </line>
    </>
  );
};

export default EmotionCurveMorph;
