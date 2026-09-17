from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent

FO_BINARY = BASE_DIR / "bin" / "fo"
FO_CONFIG_DIR = BASE_DIR / "findorb-data"

# Gaussian gravitational constant.
# AU^(3/2)/day.
GAUSSIAN_K = 0.01720209895


def _require_find_orb() -> None:
    """
    Verify that the Find_Orb executable and its runtime
    configuration are available.
    """

    if not FO_BINARY.exists():
        raise RuntimeError(
            f"Find_Orb executable not found at {FO_BINARY}.\n"
            "The deploy build (render-build.sh) must compile and install 'fo'.\n"
            "See orbit-intelligence/README.md for the required build steps."
        )

    try:
        size = FO_BINARY.stat().st_size
    except OSError as exc:
        raise RuntimeError(
            f"Cannot stat Find_Orb binary at {FO_BINARY}: {exc}"
        ) from exc

    if size < 1024:
        raise RuntimeError(
            f"Find_Orb binary at {FO_BINARY} is only {size} bytes.\n"
            "This is almost certainly an empty placeholder, not a real executable.\n"
            "Run orbit-intelligence/render-build.sh so that a properly compiled 'fo' is installed."
        )

    if not os.access(FO_BINARY, os.X_OK):
        raise RuntimeError(
            f"Find_Orb exists but is not executable: {FO_BINARY}\n"
            "Try: chmod +x " + str(FO_BINARY)
        )

    if not FO_CONFIG_DIR.exists():
        raise RuntimeError(
            f"Find_Orb configuration directory not found at {FO_CONFIG_DIR}.\n"
            "render-build.sh is responsible for creating this directory and "
            "populating it with cospar.txt + the DE430 ephemeris."
        )

    cospar_file = FO_CONFIG_DIR / "cospar.txt"
    if not cospar_file.exists():
        raise RuntimeError(
            "Find_Orb configuration is incomplete.\n"
            f"Missing required file: {cospar_file}\n"
            "This file is copied by render-build.sh from the Find_Orb source tree."
        )

    eph_candidates = list(FO_CONFIG_DIR.glob("*.430*")) + list(
        FO_CONFIG_DIR.glob("linux_p*.430*")
    )

    if not eph_candidates:
        pass


def _decimal_to_ra(ra_deg: float) -> tuple[int, int, float]:
    """Convert decimal-degree right ascension into hours, minutes, seconds."""
    total_hours = ra_deg / 15.0
    hours = int(total_hours)
    minutes_total = (total_hours - hours) * 60.0
    minutes = int(minutes_total)
    seconds = (minutes_total - minutes) * 60.0
    return hours, minutes, seconds


def _decimal_to_dec(dec_deg: float) -> tuple[str, int, int, float]:
    """Convert decimal-degree declination into sign, degrees, arcminutes, arcseconds."""
    sign = "+" if dec_deg >= 0 else "-"
    value = abs(dec_deg)
    degrees = int(value)
    minutes_total = (value - degrees) * 60.0
    minutes = int(minutes_total)
    seconds = (minutes_total - minutes) * 60.0
    return sign, degrees, minutes, seconds


def _format_mpc_date(time_utc: str) -> str:
    """
    Convert an ISO-ish UTC timestamp to MPC-style: YYYYMMDD.dddddd
    Example: 2026-09-17T12:30:00Z → 20260917.520833
    """
    value = time_utc.strip().replace("Z", "")
    if "T" not in value:
        raise ValueError(f"Invalid UTC timestamp: {time_utc}")

    date_part, time_part = value.split("T", 1)
    try:
        year, month, day = [int(x) for x in date_part.split("-")]
    except ValueError as exc:
        raise ValueError(f"Invalid UTC date: {time_utc}") from exc

    time_part = time_part.split("+")[0].split("-")[0]
    parts = time_part.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid UTC time: {time_utc}")

    hour, minute, second = int(parts[0]), int(parts[1]), float(parts[2])
    if not 0 <= hour <= 23:
        raise ValueError(f"Invalid UTC hour: {time_utc}")
    if not 0 <= minute <= 59:
        raise ValueError(f"Invalid UTC minute: {time_utc}")
    if not 0 <= second < 60:
        raise ValueError(f"Invalid UTC second: {time_utc}")

    day_fraction = (hour / 24.0) + (minute / 1440.0) + (second / 86400.0)
    return f"{year:04d}{month:02d}{day + day_fraction:09.6f}"
