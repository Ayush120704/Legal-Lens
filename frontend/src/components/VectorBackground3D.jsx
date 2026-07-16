import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

/**
 * VectorBackground3D - Interactive 3D particle network representing vector-space connections.
 * Renders a rotating point cloud with connecting lines that respond to mouse movement.
 * Mounts a canvas fixed behind all UI elements.
 */
export default function VectorBackground3D() {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // --- Scene Setup ---
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.z = 50;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // --- Particle System ---
    const PARTICLE_COUNT = 200;
    const CONNECTION_DISTANCE = 8;
    const SPREAD = 60;

    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const colors = new Float32Array(PARTICLE_COUNT * 3);
    const velocities = [];

    const colorPalette = [
      new THREE.Color(0x3b82f6), // blue
      new THREE.Color(0x8b5cf6), // purple
      new THREE.Color(0x06b6d4), // cyan
      new THREE.Color(0x10b981), // green
    ];

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      positions[i3] = (Math.random() - 0.5) * SPREAD;
      positions[i3 + 1] = (Math.random() - 0.5) * SPREAD;
      positions[i3 + 2] = (Math.random() - 0.5) * SPREAD;

      const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
      colors[i3] = color.r;
      colors[i3 + 1] = color.g;
      colors[i3 + 2] = color.b;

      velocities.push({
        x: (Math.random() - 0.5) * 0.02,
        y: (Math.random() - 0.5) * 0.02,
        z: (Math.random() - 0.5) * 0.02,
      });
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
      size: 0.4,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);

    // --- Connection Lines ---
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x3b82f6,
      transparent: true,
      opacity: 0.12,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const maxLines = 300;
    const linePositions = new Float32Array(maxLines * 6);
    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    lineGeometry.setDrawRange(0, 0);

    const lines = new THREE.LineSegments(lineGeometry, lineMaterial);
    scene.add(lines);

    // --- Mouse Interaction ---
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    const onMouseMove = (event) => {
      mouse.targetX = (event.clientX / window.innerWidth - 0.5) * 2;
      mouse.targetY = (event.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', onMouseMove);

    // --- Window Resize ---
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', onResize);

    // --- Animation Loop ---
    let animationId;
    const clock = new THREE.Clock();

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth mouse following
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      // Update particle positions
      const posArray = particleGeometry.attributes.position.array;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const i3 = i * 3;
        posArray[i3] += velocities[i].x;
        posArray[i3 + 1] += velocities[i].y;
        posArray[i3 + 2] += velocities[i].z;

        // Boundary wrapping
        if (Math.abs(posArray[i3]) > SPREAD / 2) velocities[i].x *= -1;
        if (Math.abs(posArray[i3 + 1]) > SPREAD / 2) velocities[i].y *= -1;
        if (Math.abs(posArray[i3 + 2]) > SPREAD / 2) velocities[i].z *= -1;

        // Gentle floating motion
        posArray[i3 + 1] += Math.sin(elapsed + i * 0.1) * 0.003;
      }
      particleGeometry.attributes.position.needsUpdate = true;

      // Update connection lines
      let lineIndex = 0;
      for (let i = 0; i < PARTICLE_COUNT && lineIndex < maxLines; i++) {
        for (let j = i + 1; j < PARTICLE_COUNT && lineIndex < maxLines; j++) {
          const i3 = i * 3;
          const j3 = j * 3;
          const dx = posArray[i3] - posArray[j3];
          const dy = posArray[i3 + 1] - posArray[j3 + 1];
          const dz = posArray[i3 + 2] - posArray[j3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < CONNECTION_DISTANCE) {
            const li = lineIndex * 6;
            linePositions[li] = posArray[i3];
            linePositions[li + 1] = posArray[i3 + 1];
            linePositions[li + 2] = posArray[i3 + 2];
            linePositions[li + 3] = posArray[j3];
            linePositions[li + 4] = posArray[j3 + 1];
            linePositions[li + 5] = posArray[j3 + 2];
            lineIndex++;
          }
        }
      }
      lineGeometry.setDrawRange(0, lineIndex * 2);
      lineGeometry.attributes.position.needsUpdate = true;

      // Rotate scene gently, influenced by mouse
      particles.rotation.y = elapsed * 0.03 + mouse.x * 0.3;
      particles.rotation.x = mouse.y * 0.2;
      lines.rotation.y = elapsed * 0.03 + mouse.x * 0.3;
      lines.rotation.x = mouse.y * 0.2;

      renderer.render(scene, camera);
    };

    animate();

    // --- Cleanup ---
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);

      particleGeometry.dispose();
      particleMaterial.dispose();
      lineGeometry.dispose();
      lineMaterial.dispose();
      renderer.dispose();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
}
