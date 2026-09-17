from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class OrbitType(str, Enum):
    keplerian = "keplerian"
    tle = "tle"
    state = "state"


class KeplerianElements(BaseModel):
    a: float = Field(..., description="Semi-major axis (km)")
    ecc: float = Field(..., ge=0, lt=1, description="Eccentricity")
    inc: float = Field(..., description="Inclination (deg)")
    raan: float = Field(..., description="RAAN / Longitude of ascending node (deg)")
    argp: float = Field(..., description="Argument of periapsis (deg)")
    nu: float = Field(..., description="True anomaly (deg)")
    epoch: Optional[str] = Field(None, description="ISO epoch, default now")


class TLEInput(BaseModel):
    name: Optional[str] = "Unknown"
    line1: str
    line2: str


class PropagationRequest(BaseModel):
    elements: Optional[KeplerianElements] = None
    tle: Optional[TLEInput] = None
    duration_minutes: float = Field(90.0, gt=0, le=1440)
    step_seconds: float = Field(60.0, gt=1, le=600)
    frame: str = "ITRS"  # or GCRS / TEME


class StateVector(BaseModel):
    time: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float


class PropagationResponse(BaseModel):
    success: bool
    message: str
    name: Optional[str] = None
    period_minutes: Optional[float] = None
    states: List[StateVector] = []
    ground_track: List[Dict[str, float]] = []
    meta: Dict[str, Any] = {}


class ResidualRequest(BaseModel):
    """Placeholder for future observation residual computation / Find_Orb bridge"""
    observations: List[Dict[str, Any]]
    initial_elements: KeplerianElements


class ResidualResponse(BaseModel):
    rms_arcsec: float
    chi2: float
    residuals: List[Dict[str, float]]
    note: str
