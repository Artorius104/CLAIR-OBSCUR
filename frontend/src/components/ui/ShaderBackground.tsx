'use client';

import { Canvas, useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { Vector2, Color } from 'three';

const VertexShader = `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const FragmentShader = `
uniform float uTime;
uniform vec3 uColorStart;
uniform vec3 uColorEnd;
varying vec2 vUv;

void main() {
  vec2 center = vec2(0.5, 0.5);
  float dist = distance(vUv, center);
  
  // Create ripple effect
  float wave = sin(dist * 20.0 - uTime * 1.5) * 0.5 + 0.5;
  
  // Mix colors based on distance and wave
  // Clair Obscur theme: Light vs Dark
  // Base gradient from center (light) to edge (dark)
  float strength = 1.0 - dist;
  strength += wave * 0.1;
  
  vec3 color = mix(uColorEnd, uColorStart, strength);
  
  // Add some noise/grain if possible, but keep it simple
  
  gl_FragColor = vec4(color, 1.0);
}
`;

const ShaderPlane = () => {
  const mesh = useRef<THREE.Mesh>(null);
  
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColorStart: { value: new Color('#4f46e5') }, // Indigo 600
      uColorEnd: { value: new Color('#000000') },   // Black
      uResolution: { value: new Vector2() },
    }),
    []
  );

  useFrame((state) => {
    const { clock } = state;
    if (mesh.current) {
      (mesh.current.material as THREE.ShaderMaterial).uniforms.uTime.value = clock.getElapsedTime();
    }
  });

  return (
    <mesh ref={mesh}>
      <planeGeometry args={[20, 20]} /> 
      {/* 
         Ideally we need a full screen quad. 
         Plane args [2, 2] works if we set gl_Position correctly for full screen,
         but putting a large plane in front of ortho camera works too.
      */}
      <shaderMaterial
        vertexShader={VertexShader}
        fragmentShader={FragmentShader}
        uniforms={uniforms}
      />
    </mesh>
  );
};

const ShaderBackground = () => {
  return (
    <div className="absolute inset-0 -z-10 w-full h-full bg-black">
      <Canvas camera={{ position: [0, 0, 1] }}>
        <ShaderPlane />
      </Canvas>
    </div>
  );
};

export default ShaderBackground;
