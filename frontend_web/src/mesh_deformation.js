// Need to install: npm install papaparse
import React, { useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import Papa from 'papaparse'; // 📦 Use for CSV parsing

function ColorCloud() {
  const meshRef = useRef();
  const [dataRows, setDataRows] = useState([]);
  const [originalData, setOriginalData] = useState(null);

  const radiusTop = 10;
  const radiusBottom = 10;
  const height = 25;
  const radialSegments = 256;
  const heightSegments = 256;

  // 📥 Load CSV once
  useEffect(() => {
    fetch('data/valence_arousal_timeline-screams.csv')
      .then((res) => res.text())
      .then((text) => {
        const parsed = Papa.parse(text, { header: true, dynamicTyping: true });
        const cleanedData = parsed.data.filter(
          row => typeof row.Valence === 'number' && typeof row.Arousal === 'number'
        );
        setDataRows(cleanedData);
      });
  }, []);

  // 🧱 Store original geometry data
  useEffect(() => {
    if (!meshRef.current) return;
    const geo = meshRef.current.geometry;
    const positions = geo.attributes.position.array.slice();
    const normals = geo.attributes.normal.array.slice();
    const uvs = geo.attributes.uv.array.slice();
    setOriginalData({ positions, normals, uvs });
  }, []);

  // 🎛️ Deformation logic with twist
  const displ = (a, v, u) => {
    const vNorm = (v + 1.0) * 0.5;
    const k = 5 + (1 - vNorm) * 1;

    const base = Math.sin(u * 2 * Math.PI);
    const spike = Math.max(0, Math.sin(k * u * Math.PI));

    return base * (1 + (a * 20) * spike) * (1 - vNorm);
  };

  useFrame(() => {
    if (!originalData || dataRows.length === 0) return;

    const geo = meshRef.current.geometry;
    const pos = geo.attributes.position.array;
    const count = geo.attributes.position.count;

    for (let i = 0; i < count; i++) {
      const p0x = originalData.positions[i * 3];
      const p0y = originalData.positions[i * 3 + 1];
      const p0z = originalData.positions[i * 3 + 2];
      const nx = originalData.normals[i * 3];
      const ny = originalData.normals[i * 3 + 1];
      const nz = originalData.normals[i * 3 + 2];
      const u = originalData.uvs[i * 2];
      const v = originalData.uvs[i * 2 + 1];

      const segmentIndex = Math.floor(v * dataRows.length);
      const row = dataRows[Math.min(segmentIndex, dataRows.length - 1)];

      const val = row.Valence ?? 0;
      const aro = row.Arousal ?? 0;
      const dom = row.Dominance ?? 0;

      const domNorm = (dom + 1.0) * 1;
      const twistAmount = (domNorm - 0.5) * 1.5; // [-1, 1] twist control
      const twistFreq = 60.0; // how many full twist cycles occur across the vertical height of the cylinder

      const d = displ(aro, val, u); // Don't pass dom to spike shape

      // Base displacement
      const dx = p0x + d * nx;
      const dy = p0y + d * ny;
      const dz = p0z + d * nz;

      // Twist logic: circular offset based on vertical segment
      const angle = 2 * Math.PI * twistFreq * v * twistAmount;
      const twistRadius = 1; // magnitude of twist

      const tx = dx + twistRadius * Math.sin(angle);
      const tz = dz + twistRadius * Math.cos(angle);

      pos[i * 3] = tx;
      pos[i * 3 + 1] = dy;
      pos[i * 3 + 2] = tz;
    }

    geo.attributes.position.needsUpdate = true;
    geo.computeVertexNormals();
    geo.attributes.normal.needsUpdate = true;
  });

  return (
    <mesh ref={meshRef}>
      <cylinderGeometry args={[radiusTop, radiusBottom, height, radialSegments, heightSegments, true]} />
      <meshPhongMaterial color="white" shininess={30} side={THREE.DoubleSide} />
    </mesh>
  );
}

export default function Scene() {
  return (
    <Canvas camera={{ position: [20, 20, 20], fov: 75 }}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[1, 1, 1]} intensity={1} />
      <ColorCloud />
      <OrbitControls />
    </Canvas>
  );
}
