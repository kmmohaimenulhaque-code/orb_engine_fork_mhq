"""
Core orbital mechanics engine.
Uses poliastro (validated, open-source) for propagation.
Designed so Find_Orb results can later be injected as initial elements.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict, Any
import numpy as np

from astropy import units as u
from astropy.time import Time
from poliastro.bodies import Earth
from poliastro.twobody import Orbit
from poliastro.frames import Planes

def keplerian_to_orbit(elements) -> Orbit:
    """Create a poliastro Orbit from Keplerian elements."""
    epoch = Time(elements.epoch) if elements.epoch else Time(datetime.now(timezone.utc))
    return Orbit.from_classical(
        attractor=Earth,
        a=elements.a * u.km,
        ecc=elements.ecc * u.one,
        inc=elements.inc * u.deg,
        raan=elements.raan * u.deg,
        argp=elements.argp * u.deg,
        nu=elements.nu * u.deg,
        epoch=epoch,
        plane=Planes.EARTH_EQUATOR,
    )


def tle_to_orbit(line1: str, line2: str, name: str = "TLE"):
    """
    Parse TLE via SGP4 and return a poliastro Orbit (approximate conversion).
    Full high-fidelity SGP4 propagation can be added later.
    """
    try:
        from sgp4.api import Satrec, jday
    except ImportError:
        raise RuntimeError("sgp4 package required for TLE support. pip install sgp4")

    sat = Satrec.twoline2rv(line1, line2)
    # Use current time as approx epoch for demo; real code extracts from TLE
    now = datetime.now(timezone.utc)
    jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second)
    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        raise ValueError(f"SGP4 error code {e}")
    r = r * u.km
    v = v * u.km / u.s
    epoch = Time(now)
    orb = Orbit.from_vectors(Earth, r, v, epoch=epoch)
    return orb, sat


def propagate_orbit(
    orbit: Orbit,
    duration_minutes: float = 90.0,
    step_seconds: float = 60.0,
) -> List[Dict[str, Any]]:
    """Propagate and return list of state vectors + times."""
    times = []
    states = []
    n_steps = int((duration_minutes * 60) / step_seconds) + 1
    dt = step_seconds * u.s

    for i in range(n_steps):
        t = i * dt
        # poliastro propagate
        new_orbit = orbit.propagate(t)
        r = new_orbit.r.to(u.km).value
        v = new_orbit.v.to(u.km / u.s).value
        epoch = (orbit.epoch + t).to_datetime()
        states.append({
            "time": epoch.replace(tzinfo=timezone.utc).isoformat(),
            "x": float(r[0]),
            "y": float(r[1]),
            "z": float(r[2]),
            "vx": float(v[0]),
            "vy": float(v[1]),
            "vz": float(v[2]),
        })
    return states


def ground_track_from_states(states: List[Dict]) -> List[Dict[str, float]]:
    """Very simple ECEF → lat/lon approximation (ITRS)."""
    # For demo we use a simple conversion. Production should use proper frame transforms.
    track = []
    for s in states:
        x, y, z = s["x"], s["y"], s["z"]
        r = np.sqrt(x*x + y*y + z*z)
        lat = np.degrees(np.arcsin(z / r))
        lon = np.degrees(np.arctan2(y, x))
        track.append({"lat": float(lat), "lon": float(lon), "alt_km": float(r - 6371.0)})
    return track


def compute_period_minutes(orbit: Orbit) -> float:
    return float(orbit.period.to(u.min).value)


def synthetic_residuals(elements, n_obs: int = 12) -> Dict[str, Any]:
    """
    Demo residual generator.
    In a real system this would come from Find_Orb or a least-squares fitter
    comparing predicted vs observed RA/Dec.
    """
    rng = np.random.default_rng(42)
    residuals = []
    for i in range(n_obs):
        residuals.append({
            "obs_id": i + 1,
            "ra_residual_arcsec": float(rng.normal(0, 0.8)),
            "dec_residual_arcsec": float(rng.normal(0, 0.7)),
            "time_offset_s": float(rng.normal(0, 0.05)),
        })
    ra_rms = float(np.sqrt(np.mean([r["ra_residual_arcsec"]**2 for r in residuals])))
    dec_rms = float(np.sqrt(np.mean([r["dec_residual_arcsec"]**2 for r in residuals])))
    rms = float(np.sqrt(ra_rms**2 + dec_rms**2))
    return {
        "rms_arcsec": rms,
        "chi2": rms**2 * n_obs,  # crude
        "residuals": residuals,
        "note": "Synthetic residuals for demo. Replace with Find_Orb or real least-squares when ready."
    }
