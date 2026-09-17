// NASA Orbit Simulator – Frontend
// Space Apps 2026 MVP

const API = "http://localhost:8000";

// Cesium Ion token – for demo we use the default public token path.
// For production get a free token at https://cesium.com/ion/
Cesium.Ion.defaultAccessToken = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYWE1OWUxNy1mMWZiLTQzYjYtYTQ0OS1kMWFjYmFkNjc5YzciLCJpZCI6NTc3MzMsImlhdCI6MTYyNzg0NTE5Nn0.XcKpgANiY19QB4pttv_NyWOdk_ykHAVuILszs5JqRBA";

let viewer = null;
let currentEntity = null;
let groundTrackEntity = null;

function initCesium() {
  viewer = new Cesium.Viewer("cesiumContainer", {
    terrain: Cesium.Terrain.fromWorldTerrain(),
    animation: true,
    timeline: true,
    baseLayerPicker: true,
    geocoder: false,
    homeButton: true,
    sceneModePicker: true,
    navigationHelpButton: false,
    fullscreenButton: true,
    infoBox: true,
    selectionIndicator: true,
  });

  // Darker atmosphere for space feel
  viewer.scene.globe.enableLighting = true;
  viewer.scene.skyAtmosphere.hueShift = -0.5;
  viewer.scene.skyAtmosphere.saturationShift = -0.3;
  viewer.scene.fog.enabled = true;

  // Start in 3D
  viewer.scene.mode = Cesium.SceneMode.SCENE3D;
}

async function propagate() {
  const btn = document.getElementById("propagate-btn");
  const status = document.getElementById("status");
  btn.disabled = true;
  status.textContent = "Propagating…";
  status.className = "status busy";

  const body = {
    elements: {
      a: parseFloat(document.getElementById("a").value),
      ecc: parseFloat(document.getElementById("ecc").value),
      inc: parseFloat(document.getElementById("inc").value),
      raan: parseFloat(document.getElementById("raan").value),
      argp: parseFloat(document.getElementById("argp").value),
      nu: parseFloat(document.getElementById("nu").value),
    },
    duration_minutes: parseFloat(document.getElementById("duration").value),
    step_seconds: 30,
  };

  try {
    const res = await fetch(`${API}/propagate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!data.success) {
      throw new Error(data.message || "Propagation failed");
    }

    renderOrbit(data);
    status.textContent = "Ready – Orbit loaded";
    status.className = "status ok";

    document.getElementById("sat-name").textContent = data.name || "Orbit";
    document.getElementById("period").textContent = data.period_minutes?.toFixed(2) ?? "—";
    document.getElementById("n-states").textContent = data.states.length;
    document.getElementById("info").classList.remove("hidden");
  } catch (err) {
    console.error(err);
    status.textContent = "Error: " + err.message;
    status.className = "status";
    alert("Backend not reachable or error:\n" + err.message + "\n\nMake sure the FastAPI server is running on port 8000.");
  } finally {
    btn.disabled = false;
  }
}

function renderOrbit(data) {
  // Clear previous
  if (currentEntity) viewer.entities.remove(currentEntity);
  if (groundTrackEntity) viewer.entities.remove(groundTrackEntity);

  const positions = data.states.map(s =>
    Cesium.Cartesian3.fromElements(s.x * 1000, s.y * 1000, s.z * 1000)
  );

  // Satellite path (trail)
  currentEntity = viewer.entities.add({
    name: data.name || "Satellite",
    polyline: {
      positions: positions,
      width: 2.5,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.25,
        color: Cesium.Color.CYAN,
      }),
      clampToGround: false,
    },
    position: positions[0],
    point: {
      pixelSize: 12,
      color: Cesium.Color.ORANGE,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2,
      heightReference: Cesium.HeightReference.NONE,
    },
    label: {
      text: data.name || "SAT",
      font: "14px sans-serif",
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(0, -18),
    },
  });

  // Simple ground track (lat/lon)
  if (data.ground_track && data.ground_track.length > 1) {
    const gtPositions = data.ground_track.map(p =>
      Cesium.Cartesian3.fromDegrees(p.lon, p.lat, 0)
    );
    groundTrackEntity = viewer.entities.add({
      name: "Ground Track",
      polyline: {
        positions: gtPositions,
        width: 1.5,
        material: Cesium.Color.LIME.withAlpha(0.7),
        clampToGround: true,
      },
    });
  }

  // Fly to the orbit
  viewer.flyTo(currentEntity, {
    duration: 1.8,
    offset: new Cesium.HeadingPitchRange(0, Cesium.Math.toRadians(-35), 2.5e7),
  });
}

async function loadSample(which) {
  try {
    const res = await fetch(`${API}/sample/${which}`);
    const data = await res.json();
    const e = data.elements;
    document.getElementById("a").value = e.a;
    document.getElementById("ecc").value = e.ecc;
    document.getElementById("inc").value = e.inc;
    document.getElementById("raan").value = e.raan;
    document.getElementById("argp").value = e.argp;
    document.getElementById("nu").value = e.nu;
    // Switch to Kepler tab
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelector('[data-tab="kepler"]').classList.add("active");
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    document.getElementById("kepler-tab").classList.add("active");
  } catch (err) {
    alert("Could not load sample. Is the backend running?");
  }
}

// Tab switching
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab + "-tab").classList.add("active");
  });
});

document.getElementById("propagate-btn").addEventListener("click", propagate);

// Init
initCesium();
console.log("NASA Orbit Simulator frontend ready");
