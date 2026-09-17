"""
NASA Orbit Simulator – FastAPI Backend
Space Apps 2026 MVP
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timezone
from pathlib import Path
import traceback

from models import (
    PropagationRequest,
    PropagationResponse,
    StateVector,
    ResidualRequest,
    ResidualResponse,
    KeplerianElements,
    TLEInput,
)
from orbit_engine import (
    keplerian_to_orbit,
    propagate_orbit,
    ground_track_from_states,
    compute_period_minutes,
    synthetic_residuals,
)

app = FastAPI(
    title="NASA Orbit Simulator API",
    description="Interactive 3D orbit propagation & residual engine for Space Apps 2026",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files (works on Render + local)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def root():
    """Serve the 3D frontend when available, otherwise JSON status."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "project": "NASA-Grade Interactive 3D Orbit Simulator",
        "status": "online",
        "docs": "/docs",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "message": "Ready for Space Apps 2026 demo",
    }


@app.get("/app.js")
def serve_app_js():
    f = FRONTEND_DIR / "app.js"
    if f.exists():
        return FileResponse(f, media_type="application/javascript")
    raise HTTPException(404)


@app.get("/style.css")
def serve_style():
    f = FRONTEND_DIR / "style.css"
    if f.exists():
        return FileResponse(f, media_type="text/css")
    raise HTTPException(404)


@app.get("/health")
def health():
    return {"status": "ok", "engine": "poliastro + astropy"}


@app.post("/propagate", response_model=PropagationResponse)
def propagate(req: PropagationRequest):
    """
    Propagate an orbit from Keplerian elements or TLE.
    Returns Cartesian states + ground track suitable for Cesium.
    """
    try:
        if req.elements is None and req.tle is None:
            raise HTTPException(400, "Provide either 'elements' or 'tle'")

        name = "Custom Orbit"
        if req.elements:
            orbit = keplerian_to_orbit(req.elements)
            name = "Keplerian"
        else:
            # For MVP we convert TLE to approximate Keplerian
            # Full SGP4 path can be added later
            from orbit_engine import tle_to_orbit
            orbit, _ = tle_to_orbit(req.tle.line1, req.tle.line2, req.tle.name or "TLE")
            name = req.tle.name or "TLE Object"

        states_raw = propagate_orbit(
            orbit,
            duration_minutes=req.duration_minutes,
            step_seconds=req.step_seconds,
        )
        states = [StateVector(**s) for s in states_raw]
        track = ground_track_from_states(states_raw)
        period = compute_period_minutes(orbit)

        return PropagationResponse(
            success=True,
            message="Propagation successful",
            name=name,
            period_minutes=period,
            states=states,
            ground_track=track,
            meta={
                "frame": req.frame,
                "duration_min": req.duration_minutes,
                "step_s": req.step_seconds,
                "engine": "poliastro",
                "note": "For high-fidelity LEO use SGP4 path (future)",
            },
        )
    except Exception as e:
        traceback.print_exc()
        return PropagationResponse(
            success=False,
            message=str(e),
            states=[],
            ground_track=[],
            meta={"error": str(e)},
        )


@app.post("/residuals", response_model=ResidualResponse)
def residuals(req: ResidualRequest):
    """
    Demo residual endpoint.
    In production this would call Find_Orb or a least-squares fitter
    against real optical/radar observations.
    """
    result = synthetic_residuals(req.initial_elements)
    return ResidualResponse(**result)


@app.get("/sample/iss")
def sample_iss():
    """Return a ready-to-use ISS-like Keplerian set for quick demo."""
    return {
        "name": "ISS (approx)",
        "elements": {
            "a": 6778.0,
            "ecc": 0.0005,
            "inc": 51.64,
            "raan": 30.0,
            "argp": 0.0,
            "nu": 0.0,
            "epoch": datetime.now(timezone.utc).isoformat(),
        },
        "note": "Approximate. For real TLEs use Celestrak.",
    }


@app.get("/sample/starlink")
def sample_starlink():
    return {
        "name": "Starlink-like",
        "elements": {
            "a": 6921.0,
            "ecc": 0.0001,
            "inc": 53.0,
            "raan": 120.0,
            "argp": 0.0,
            "nu": 45.0,
            "epoch": datetime.now(timezone.utc).isoformat(),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
