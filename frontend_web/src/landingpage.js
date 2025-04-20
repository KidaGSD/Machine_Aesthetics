import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { frostedGlassShader } from './shaders/frostedGlassShader';
import './App.css';
import { useNavigate } from "react-router-dom";

const LandingPage = () => {
  const mountRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#f2f2f2');

    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 5.5;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.physicallyCorrectLights = true;
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const mount = mountRef.current;
    if (mount) {
      mount.appendChild(renderer.domElement);
    }

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.1);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.1);
    directionalLight.position.set(10, 0, 0);
    scene.add(directionalLight);

    const tableGeometry = new THREE.BoxGeometry(20, 2, 3);
    const tableMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      roughness: 0.4,
      metalness: 0,
      transmission: 0.9,
      transparent: true,
      opacity: 0.3,
      thickness: 1,
      clearcoat: 1,
      clearcoatRoughness: 0.1,
    });

    const tableCube = new THREE.Mesh(tableGeometry, tableMaterial);
    tableCube.position.set(8, -2, 0);
    scene.add(tableCube);

    // Mesh refs for interaction
    const meshRefs = [];

    const stlLoader = new STLLoader();
    const models = [
      { path: '/models/mesh01.stl', pos: [0, 0, 0], color: 0xffe561 },
      { path: '/models/mesh02.stl', pos: [2.5, 0, 0], color: 0x88ddff, customShader: true },
      { path: '/models/mesh03.stl', pos: [5.5, 0, 0], color: 0x88ddff, customShader: true },
    ];

    models.forEach(({ path, pos, color, customShader }, idx) => {
      stlLoader.load(path, (geometry) => {
        const shader = frostedGlassShader.clone();
        if (customShader && idx === 1) {
          shader.uniforms.uColorTop.value = new THREE.Color(0xE1DDDE);
          shader.uniforms.uColorMiddle.value = new THREE.Color(0xCBC7C3);
          shader.uniforms.uColorBottom.value = new THREE.Color(0x99AE81);
        }
        if (customShader && idx === 2) {
          shader.uniforms.uColorTop.value = new THREE.Color(0xE1DDDE);
          shader.uniforms.uColorMiddle.value = new THREE.Color(0xCBC7C3);
          shader.uniforms.uColorBottom.value = new THREE.Color(0xCED0DF);
        }

        const mesh = new THREE.Mesh(geometry, shader);
        mesh.scale.set(0.08, 0.08, 0.08);
        mesh.position.set(...pos);
        scene.add(mesh);
        meshRefs.push(mesh);

        const light = new THREE.PointLight(color, 0.5, 10);
        light.position.copy(mesh.position);
        scene.add(light);
      });
    });

    // Smooth camera zoom
    let zoomProgress = 0;
    const initialZ = 5.5;
    const targetZ = 5;

    // Smooth rotation based on mouse X
    let targetRotation = 0;
    let currentRotation = 0;

    // Raycaster setup
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let hoveredMesh = null;

    const onMouseMove = (e) => {
      pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.y = -(e.clientY / window.innerHeight) * 2 + 1;
      targetRotation = (e.clientX / window.innerWidth - 0.5) * 0.2;
    };
    window.addEventListener('mousemove', onMouseMove);

    const animate = () => {
      requestAnimationFrame(animate);

      if (zoomProgress < 1) {
        zoomProgress += 0.01;
        const eased = initialZ + (targetZ - initialZ) * easeOutCubic(zoomProgress);
        camera.position.z = eased;
      }

      // Smooth camera orbit
      currentRotation += (targetRotation - currentRotation) * 0.05;
      camera.position.x = Math.sin(currentRotation) * 3;
      camera.lookAt(0, 0, 0);

      // Raycasting for hover detection
      raycaster.setFromCamera(pointer, camera);
      const intersects = raycaster.intersectObjects(meshRefs);
      hoveredMesh = intersects.length > 0 ? intersects[0].object : null;

      // Animate hovered mesh rotation
      meshRefs.forEach((mesh) => {
        if (mesh === hoveredMesh) {
          mesh.rotation.y += 0.01;
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    function easeOutCubic(t) {
      return 1 - Math.pow(1 - t, 3);
    }

    const handleResize = () => {
      renderer.setSize(window.innerWidth, window.innerHeight);
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', handleResize);
      if (mount && renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [navigate]);

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <div ref={mountRef} className="absolute inset-0 z-0" />
      <div
        style={{
          display: 'flex',
          width: '1280px',
          padding: '0px 60px',
          flexDirection: 'column',
          alignItems: 'flex-start',
          gap: '9px',
          height: '100vh',
          justifyContent: 'center',
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: 10,
          color: '#000',
        }}
      >
        <h2 className="text-animate" style={{ fontWeight: '500', fontSize: '16px', marginBottom: '0px' }}>
          Luminote
        </h2>
        <h1 className="text-animate" style={{ fontWeight: '600', fontSize: '24px', marginBottom: '8px' }}>
          Generate Your Lamp Design From Voices
        </h1>
        <button
          className="custom-button text-animate"
          onClick={() => navigate('/lampcreation')}
        >
          Start Creating Now
        </button>
      </div>
    </div>
  );
};

export default LandingPage;

/* Text Animations */
const styleSheet = document.createElement("style");
styleSheet.innerText = `
  @keyframes fadeInUp {
    0% {
      opacity: 0;
      transform: translateY(10px);
      filter: blur(6px);
    }
    100% {
      opacity: 1;
      transform: translateY(0);
      filter: blur(0);
    }
  }

  .text-animate {
    animation: fadeInUp 1s ease-out forwards;
  }
`;
document.head.appendChild(styleSheet);
