import {
  Canvas,
  useFrame,
} from "@react-three/fiber";

import {
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

      <sphereGeometry
        args={[0.12, 32, 32]}
      />

      <meshBasicMaterial />

    </mesh>
  );
}


function Earth() {

  return (
    <mesh position={[1, 0, 0]}>

      <sphereGeometry
        args={[0.035, 24, 24]}
      />

      <meshStandardMaterial />

    </mesh>
  );
}


function OrbitLine({
  points,
}) {

  const geometry =
    useMemo(() => {

      const array = [];

      for (const point of points) {
        array.push(
          point[0],
          point[1],
          point[2]
        );
      }

      return array;

    }, [points]);


  return (
    <line>

      <bufferGeometry>

        <bufferAttribute
          attach="attributes-position"
          count={points.length}
          array={
            new Float32Array(
              geometry
            )
          }
          itemSize={3}
        />

      </bufferGeometry>

      <lineBasicMaterial />

    </line>
  );
}


function ObjectMarker({
  points,
}) {

  const ref = useRef();

  useFrame(({ clock }) => {

    if (!ref.current || !points.length) {
      return;
    }

    const index =
      Math.floor(
        (
          clock.getElapsedTime() * 12
        ) %
        points.length
      );

    const point =
      points[index];

    if (!point) {
      return;
    }

    ref.current.position.set(
      point[0],
      point[1],
      point[2]
    );

  });


  return (
    <mesh ref={ref}>

      <sphereGeometry
        args={[0.045, 16, 16]}
      />

      <meshStandardMaterial />

    </mesh>
  );
}


function ReferenceGrid() {

  return (
    <gridHelper
      args={[6, 24]}
      rotation={[
        Math.PI / 2,
        0,
        0,
      ]}
    />
  );
}


function Scene({
  points,
}) {

  return (
    <>
      <ambientLight intensity={0.8} />

      <pointLight
        position={[0, 0, 0]}
        intensity={10}
      />

      <Stars
        radius={20}
        depth={10}
        count={1800}
        factor={2}
        saturation={0}
        fade
      />

      <Sun />

      <Earth />

      {points.length > 1 && (
        <>
          <OrbitLine points={points} />

          <ObjectMarker
            points={points}
          />
        </>
      )}

      <ReferenceGrid />

      <OrbitControls
        enableDamping
        dampingFactor={0.08}
        minDistance={1.2}
        maxDistance={12}
      />

    </>
  );
}


export default function OrbitViewer({
  orbitPath,
}) {

  return (
    <Canvas
      camera={{
        position: [2.7, 2.1, 3.5],
        fov: 45,
        near: 0.01,
        far: 100,
      }}
      dpr={[1, 2]}
    >

      <Scene
        points={orbitPath}
      />

    </Canvas>
  );
}
