import React, { useRef, useEffect, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import Papa from "papaparse";

function ColorCloud({ csvPath }) {
  const meshRef = useRef();
  const [dataRows, setDataRows] = useState([]);
  const [originalData, setOriginalData] = useState(null);

  const radiusTop = 10;
  const radiusBottom = 10;
  const height = 25;
  const radialSegments = 256;
  const heightSegments = 256;

  useEffect(() => {
    if (!csvPath || !meshRef.current) return;

    const geo = meshRef.current.geometry;
    const originalPositions = geo.attributes.position.array.slice();
    const originalNormals = geo.attributes.normal.array.slice();
    const originalUVs = geo.attributes.uv.array.slice();
    setOriginalData({
      positions: originalPositions,
      normals: originalNormals,
      uvs: originalUVs,
    });

    fetch(csvPath + `?t=${Date.now()}`)
      .then((res) => res.text())
      .then((text) => {
        const parsed = Papa.parse(text, { header: true, dynamicTyping: true });
        const cleanedData = parsed.data.filter(row =>
          typeof row.Valence === 'number' &&
          typeof row.Arousal === 'number' &&
          typeof row.Dominance === 'number'
        );
        setDataRows(cleanedData);
      });
  }, [csvPath]);

  const displ = (a, v, u) => {
    const vNorm = (v + 1.0) * 0.5;
    const k = 5 + (1 - vNorm) * 1;
    const base = Math.sin(u * 2 * Math.PI);
    const spike = Math.max(0, Math.sin(k * u * Math.PI));
    return base * (1 + a * 20 * spike) * (1 - vNorm);
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

      const index = Math.floor(v * dataRows.length);
      const row = dataRows[Math.min(index, dataRows.length - 1)];

      const val = row.Valence ?? 0;
      const aro = row.Arousal ?? 0;
      const dom = row.Dominance ?? 0;

      const d = displ(aro, val, u);
      const domNorm = (dom + 1.0) * 1;
      const twistAmount = (domNorm - 0.5) * 1.5;
      const twistFreq = 60.0;

      const dx = p0x + d * nx;
      const dy = p0y + d * ny;
      const dz = p0z + d * nz;

      const angle = 2 * Math.PI * twistFreq * v * twistAmount;
      const twistRadius = 1;

      const tx = dx + twistRadius * Math.sin(angle);
      const tz = dz + twistRadius * Math.cos(angle);

      pos[i * 3] = tx;
      pos[i * 3 + 1] = dy;
      pos[i * 3 + 2] = tz;
    }

    geo.attributes.position.needsUpdate = true;
    geo.attributes.normal.needsUpdate = true;
    geo.computeVertexNormals();
  });

  return (
    <>
      {/* Point light inside the mesh */}
      <pointLight position={[0, 0, 0]} intensity={1000} distance={10000} color="orange" />
      
      <mesh ref={meshRef}>
        <cylinderGeometry
          args={[radiusTop, radiusBottom, height, radialSegments, heightSegments, true]}
        />
        <meshPhysicalMaterial
          color="white"
          roughness={0.7}
          transmission={0.6} // glassy look
          thickness={2.0}
          transparent={true}
          opacity={0.9}
          side={THREE.DoubleSide}
        />
      </mesh>
    </>
  );
}

export default function Scene({ csvPath }) {
  return (
    <Canvas camera={{ position: [20, 20, 20], fov: 75 }}>
      <ambientLight intensity={0.2} />
      <directionalLight position={[10, 10, 10]} intensity={0.8} />
      <ColorCloud csvPath={csvPath} />
      <OrbitControls />
    </Canvas>
  );
}
