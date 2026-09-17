
from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from orbital_service import solve_orbit


app = FastAPI(
    title="Orbit Intelligence API",
    version="0.1.0",
    description="Orbit determination interface powered by Bill Gray's Find_Orb.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Observation(BaseModel):
    """
    One optical astrometric observation.

    ra_deg / dec_deg are decimal degrees.
    time_utc should be an ISO-8601 UTC timestamp.
    """

    time_utc: str = Field(..., description="UTC observation timestamp")
    ra_deg: float = Field(..., ge=0.0, lt=360.0)
    dec_deg: float = Field(..., ge=-90.0, le=90.0)
    magnitude: float | None = Field(default=None, ge=-10.0, le=40.0)


class OrbitRequest(BaseModel):
    object_name: str = Field(default="MHA-TEST", min_length=1, max_length=40)
    observations: List[Observation] = Field(..., min_length=3)


@app.get("/")
def root():
    return {
        "name": "Orbit Intelligence API",
        "version": "0.1.0",
        "engine": "Bill Gray Find_Orb",
        "status": "online",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post("/api/orbit/solve")
def calculate_orbit(request: OrbitRequest):
    try:
        return solve_orbit(
            object_name=request.object_name,
            observations=request.observations,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
