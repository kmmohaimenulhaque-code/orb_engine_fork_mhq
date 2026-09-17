import {
  Canvas,
  useFrame,
} from "@react-three/fiber";

import {
  Line,
  OrbitControls,
  Stars,
} from "@react-three/drei";

import {
  useMemo,
  useRef,
} from "react";


function Sun() {
  return (
    <mesh>
      <sphereGeometry args={[0.12, 32, 32]} />
      <meshBasicMaterial color="#ffcc55" />
    </mesh>
  );
}


function Earth() {
  return (
    <mesh position={[1, 0, 0]}>
      <sphereGeometry args={[0.035, 24, 24]} />
      <meshStandardMaterial
        color="#4aa3ff"
        emissive="#1a3a6a"
        emissiveIntensity={0.35}
      />
    </mesh>
  );
}


function OrbitPath({
  points,
}) {
  const positions = useMemo(() => {
    if (!points || points.length < 2) {
      return [];
    }

    return points.map((p) => [
      Number(p[0]) || 0,
      Number(p[1]) || 0,
      Number(p[2]) || 0,
    ]);
  }, [points]);

  if (positions.length < 2) {
    return null;
  }

  return (
    <Line
      points={positions}
      color="#7ec8ff"
      lineWidth={1.6}
      transparent
      opacity={0.9}
    />
  );
}


function ObjectMarker({
  points,
}) {
  const ref = useRef();

  useFrame(({ clock }) => {
    if (!ref.current || !points || points.length === 0) {
      return;
    }

    const index = Math.floor(
      (clock.getElapsedTime() * 10) % points.length
    );

    const point = points[index];

    if (!point) {
      return;
    }

    ref.current.position.set(
      Number(point[0]) || 0,
      Number(point[1]) || 0,
      Number(point[2]) || 0
    );
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.05, 16, 16]} />
      <meshStandardMaterial
        color="#ff6b6b"
        emissive="#ff3030"
        emissiveIntensity={0.55}
      />
    </mesh>
  );
}


function ReferenceGrid() {
  return (
    <gridHelper
      args={[8, 32, "#1e2a3c", "#141c28"]}
      rotation={[Math.PI / 2, 0, 0]}
    />
  );
}


function Scene({
  points,
}) {
  return (
    <>
      <color attach="background" args={["#05070c"]} />

      <ambientLight intensity={0.55} />

      <pointLight
        position={[0, 0, 0]}
        intensity={18}
        distance={20}
        decay={1.4}
        color="#fff0c0"
      />

      <directionalLight
        position={[4, 6, 3]}
        intensity={0.6}
        color="#a8c4ff"
      />

      <Stars
        radius={40}
        depth={18}
        count={2200}
        factor={2.2}
        saturation={0}
        fade
        speed={0.4}
      />

      <Sun />
      <Earth />

      {points && points.length > 1 && (
        <>
          <OrbitPath points={points} />
          <ObjectMarker points={points} />
        </>
      )}

      <ReferenceGrid />

      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        minDistance={1.4}
        maxDistance={18}
        target={[0, 0, 0]}
      />
    </>
  );
}


export default function OrbitViewer({
  orbitPath = [],
}) {
  return (
    <Canvas
      camera={{
        position: [2.8, 2.2, 3.6],
        fov: 45,
        near: 0.01,
        far: 200,
      }}
      dpr={[1, 1.75]}
      gl={{
        antialias: true,
        alpha: false,
      }}
    >
      <Scene points={orbitPath} />
    </Canvas>
  );
}
