import { useEffect, useRef } from "react";
import * as THREE from "three";

import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { int } from "three/tsl";


const Game = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current!;

    const mouse = new THREE.Vector2();

    function onMouseMove(event: MouseEvent) {
      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = - (event.clientY / window.innerHeight) * 2 + 1; // note the minus
    }

    window.addEventListener("mousemove", onMouseMove);
    
    // Scene
    const scene = new THREE.Scene();

    // Camera
    const camera = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.z = 3;
    camera.position.y = 2;

    // Add ambient light so everything is at least slightly visible
    scene.add(new THREE.AmbientLight(0xffffff, 0.5));

    // Add a directional light for shading
    const dirLight = new THREE.DirectionalLight(0xffffff, 1);
    dirLight.position.set(10, 10, 10);
    scene.add(dirLight);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // OBJ Loader
    const loader = new OBJLoader();

    let tankHead: THREE.Mesh | null = null;
    let tankBody: THREE.Mesh | null = null;

    loader.load(
      // URL to OBJ file
      'http://localhost:8000/api/v1/models/player_tank',
      (obj) => {
        // Center object
        const materials: Record<string, THREE.Color> = {
          'TankBody': new THREE.Color(0, 0.290196, 0.721569),
          'TankTracks': new THREE.Color(0, 0.600000, 0.86274),
          'TankWheels': new THREE.Color( 0.137255, 0.470588, 0.611765),
          'TankBarrel': new THREE.Color(0.050980, 0.203921, 0.301961),
          'TankUnderbody': new THREE.Color(0.039216, 0.066667, 0.639216),
        };
        console.log('materials', materials)
        obj.rotateY(Math.PI / 2); // Rotate 180 degrees to face forward
        obj.rotateX(-Math.PI / 2); // Rotate to lie flat
        obj.rotateZ(Math.PI / 2)

        obj.traverse((child) => {
          const mesh = child as THREE.Mesh;
          if (mesh.isMesh) {
            const meshMaterials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
            meshMaterials.forEach((material) => {
              const color = materials[material.name];
              if (color != undefined) {
                (material as THREE.MeshStandardMaterial).color.set(color);
              }
            });
          }
        });
        console.log('OBJ loaded:', obj);
        obj.children.forEach((child) => {
          if (child.name === 'Body') {
            tankBody = child as THREE.Mesh;
          } else if (child.name === 'Head') {
            tankHead = child as THREE.Mesh;
          }
        });
        obj.position.set(0, 0, 0);
        scene.add(obj);
        const marker = new THREE.Mesh(new THREE.SphereGeometry(0.05), new THREE.MeshBasicMaterial({color:0xff0000}));
        obj.add(marker);

      },
      (progress) => {
        console.log(`Loading: ${Math.round((progress.loaded / progress.total) * 100)}%`);
      },
      (error) => {
        console.error('Error loading OBJ', error);
      }
    );

    const raycaster = new THREE.Raycaster();
    // size of the plane
    const planeSize = 1000;

    // Plane geometry (width, height)
    const geometry = new THREE.PlaneGeometry(planeSize, planeSize);

    // Plane material (color, double-sided)
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(150 / 255, 75 / 255, 0),
      side: THREE.DoubleSide, // make it visible from both sides
    });

    // Mesh
    const planeMesh = new THREE.Mesh(geometry, material);
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0); // horizontal Y-up plane

    // Rotate plane so it lies on the X-Y plane at z = 0
    planeMesh.rotation.x = -Math.PI / 2; // rotate around X to make normal point up
    planeMesh.position.z = 0; // optional, place at z=0

    // Add to scene
    scene.add(planeMesh);

    const intersectPoint = new THREE.Vector3();

    const intersection2D = new THREE.Vector2();
    const tankPosition2D = new THREE.Vector2();

    scene.add(new THREE.AxesHelper(1)); // world axes

    // Animate
    let animationId: number;
    const animate = () => {
      controls.update();

      // intersectPoint now contains the x, y, z coordinates on the plane
      //console.log('intersect', intersectPoint.x, intersectPoint.y, intersectPoint.z);
      if (tankHead != null && tankBody != null) {
        // Compute angle between tank position and intersect point
        raycaster.setFromCamera(mouse, camera);
        raycaster.ray.intersectPlane(plane, intersectPoint);
        intersection2D.set(intersectPoint.x, intersectPoint.z);
        const angle = Math.atan2(
          intersection2D.y - tankBody.position.z,
          intersection2D.x - tankBody.position.x
        );
        console.log('pos', tankHead.position)
        tankHead.rotation.z = -angle + (Math.PI * 2);
      }
      renderer.render(scene, camera);
      animationId = requestAnimationFrame(animate);
    };

    animate();

    // Resize
    const onResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", onResize);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouseMove);
      container.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);


  return <div ref={containerRef} style={{ width: "100%", height: "100%"}} />;

}

export default Game