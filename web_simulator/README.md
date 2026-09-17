# NASA-Grade Interactive 3D Orbit Simulator
### Space Apps 2026 – Real Science + Live Visualization MVP

**Thesis**  
Real observations / TLEs / Keplerian elements → rigorous orbital mechanics (poliastro + astropy) → interactive CesiumJS 3D visualization with uncertainty, residuals, and NASA data links.

This is a **working prototype** designed for a realistic 48-hour Space Apps build.  
It prioritizes: **Impact · Validity · Relevance · Presentation**.

---

## Quick Start (2 minutes)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
# Just open index.html in a modern browser
# or serve it:
python -m http.server 3000
```

Then open: http://localhost:3000

Backend API docs: http://localhost:8000/docs

---

## Architecture

```
INPUT (TLE / Keplerian / Observations)
        ↓
   FastAPI Backend
   • Orbit propagation (poliastro)
   • State vectors & ephemeris
   • Simple least-squares residual demo
   • Covariance / uncertainty stub
        ↓
   JSON / WebSocket
        ↓
   CesiumJS Frontend
   • 3D Earth + satellite trail
   • Ground track
   • Time control
   • Uncertainty visualization (placeholder)
```

**NASA Data Path**  
- Celestrak TLEs  
- JPL Horizons (can be added)  
- MPC observations (future Find_Orb integration)

---

## Project Structure

```
nasa-orbit-sim/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── orbit_engine.py      # Core orbital mechanics
│   ├── models.py            # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Cesium 3D viewer
│   ├── app.js               # Main frontend logic
│   └── style.css
├── data/
│   └── sample_tles.txt      # Demo TLEs
├── docs/
│   └── JUDGING.md           # How this maps to Space Apps criteria
├── scripts/
│   └── demo_run.sh
└── README.md
```

---

## What Works Right Now (MVP)

- Load sample TLEs or paste Keplerian elements
- Propagate orbit and return Cartesian states
- Interactive Cesium 3D globe with satellite trail
- Time scrubbing / play-pause
- Ground track projection
- Residual demo endpoint (for future Find_Orb hook)
- Clear API documentation (OpenAPI)

## What is Intentionally Deferred (honest scope)

- Full Find_Orb C++ integration (needs container + wrapper)
- Live radar/optical observation ingestion
- Full covariance ellipsoid rendering
- Multi-satellite constellation
- SPICE kernel support

These are excellent “Next 3 Actions” for the team.

---

## Validation Approach

1. Compare propagated positions against known published orbits (e.g. ISS, Starlink).
2. Residual RMS on synthetic observations.
3. Visual inspection of ground tracks vs public tools (Celestrak, Heavens-Above).
4. Document assumptions and uncertainty sources in every response.

---

## Space Apps Judging Alignment

| Criterion     | How this project addresses it                          |
|---------------|--------------------------------------------------------|
| Impact        | Real orbital mechanics + public NASA/Celestrak data    |
| Creativity    | Interactive 3D + residual/uncertainty path             |
| Validity      | poliastro (validated library) + explicit assumptions   |
| Relevance     | Directly uses orbital determination science            |
| Presentation  | Clean Cesium demo + clear architecture + fallback      |

---

## Next 3 Actions (recommended)

1. Add a simple least-squares fitter that accepts RA/Dec observations and returns fitted elements (bridge to Find_Orb).
2. Containerize with Docker so judges can run with one command.
3. Add live Celestrak TLE fetch + one real asteroid orbit from JPL Horizons.

---

Built for NASA Space Apps 2026.  
Real problem → Real science → Working prototype → Unforgettable demo.
