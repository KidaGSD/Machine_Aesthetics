import React, { useEffect, useState } from "react";
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

function MeshFromShape({ shape }) {
  const geometry = new THREE.BufferGeometry();

  // Flatten the vertices and faces
  const vertices = new Float32Array(shape.vertices.flat());
  const indices = new Uint32Array(shape.faces.flat());

  // Build the geometry
  geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(vertices, 3)
  );
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  geometry.computeVertexNormals();

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color="tomato" />
    </mesh>
  );
}

export default function MeshViewer() {
  const [shapeData, setShapeData] = useState(null);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/shape")
      .then((res) => res.json())
      .then(setShapeData)
      .catch((err) => console.error("Error fetching shape:", err));
  }, []);

  return (
    <Canvas camera={{ position: [0, 0, 100], fov: 45 }}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} />
      <OrbitControls />
      {shapeData && <MeshFromShape shape={shapeData} />}
    </Canvas>
  );
}
