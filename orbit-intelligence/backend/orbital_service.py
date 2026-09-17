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


# Gaussian gravitational constant.
# AU^(3/2) / day.
GAUSSIAN_K = 0.01720209895


def _require_find_orb() -> None:
    if not FO_BINARY.exists():
        raise RuntimeError(
            f"Find_Orb executable not found at {FO_BINARY}. "
            "Build the upstream 'fo' executable and place it there."
        )

    if not os.access(FO_BINARY, os.X_OK):
        raise RuntimeError(
            f"Find_Orb exists but is not executable: {FO_BINARY}"
        )


def _decimal_to_ra(ra_deg: float) -> tuple[int, int, float]:
    total_hours = ra_deg / 15.0

    hours = int(total_hours)
    minutes_total = (total_hours - hours) * 60.0
    minutes = int(minutes_total)
    seconds = (minutes_total - minutes) * 60.0

    return hours, minutes, seconds


def _decimal_to_dec(dec_deg: float) -> tuple[str, int, int, float]:
    sign = "+" if dec_deg >= 0 else "-"

    value = abs(dec_deg)

    degrees = int(value)
    minutes_total = (value - degrees) * 60.0
    minutes = int(minutes_total)
    seconds = (minutes_total - minutes) * 60.0

    return sign, degrees, minutes, seconds


def _format_mpc_date(time_utc: str) -> str:
    """
    Convert ISO-ish UTC timestamp to MPC-style:

        YYYY MM DD.dddddd

    Example:

        2026-09-17T12:30:00Z

    becomes approximately:

        2026 09 17.520833
    """

    value = time_utc.strip().replace("Z", "")

    if "T" not in value:
        raise ValueError(
            f"Invalid UTC timestamp: {time_utc}"
        )

    date_part, time_part = value.split("T", 1)

    year, month, day = [int(x) for x in date_part.split("-")]

    time_part = time_part.split("+")[0]

    hour, minute, second = time_part.split(":")
    hour = int(hour)
    minute = int(minute)
    second = float(second)

    day_fraction = (
        hour / 24.0
        + minute / 1440.0
        + second / 86400.0
    )

    return f"{year:04d} {month:02d} {day + day_fraction:09.6f}"


def _format_observation(
    object_name: str,
    time_utc: str,
    ra_deg: float,
    dec_deg: float,
    magnitude: float | None,
) -> str:

    ra_h, ra_m, ra_s = _decimal_to_ra(ra_deg)
    dec_sign, dec_d, dec_m, dec_s = _decimal_to_dec(dec_deg)

    date_string = _format_mpc_date(time_utc)

    # MPC 80-column optical observation format.
    #
    # The exact astrometric provenance / observatory code matters for
    # production orbit determination. For this standalone simulator
    # we use a synthetic geocentric code and clearly mark the output
    # as a demonstration orbit solution.
    mag = f"{magnitude:4.1f}" if magnitude is not None else "    "

    line = (
        f"{object_name[:12]:<12}"
        f" C"
        f"{date_string:>17}"
        f" {ra_h:02d} {ra_m:02d} {ra_s:05.2f}"
        f" {dec_sign}{dec_d:02d} {dec_m:02d} {dec_s:04.1f}"
        f"          "
        f"{mag}"
        f" 500"
    )

    return line[:80]


def _run_find_orb(input_file: Path, output_dir: Path) -> str:
    """
    Run the non-interactive Find_Orb executable.

    Find_Orb normally writes JSON products such as total.json into
    its working/configuration environment.
    """

    command = [
        str(FO_BINARY),
        str(input_file),
        "-v",
    ]

    env = os.environ.copy()

    # Keep Find_Orb's generated files isolated from the user's
    # normal ~/.find_orb directory.
    env["HOME"] = str(output_dir)

    try:
        process = subprocess.run(
            command,
            cwd=output_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=45,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Find_Orb exceeded the 45-second execution limit."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Could not execute Find_Orb: {exc}"
        ) from exc

    combined_output = (
        process.stdout
        + "\n"
        + process.stderr
    )

    if process.returncode != 0:
        raise RuntimeError(
            "Find_Orb failed.\n\n"
            + combined_output[-5000:]
        )

    return combined_output


def _find_json_files(directory: Path) -> list[Path]:
    return list(directory.rglob("*.json"))


def _load_best_find_orb_json(directory: Path) -> dict[str, Any]:
    candidates = _find_json_files(directory)

    preferred = [
        p for p in candidates
        if p.name.lower() in {
            "total.json",
            "elements.json",
            "short.json",
        }
    ]

    candidates = preferred or candidates

    for path in candidates:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data

        except (OSError, json.JSONDecodeError):
            continue

    raise RuntimeError(
        "Find_Orb completed but no readable JSON result was produced."
    )


def _recursive_find_key(
    value: Any,
    keys: set[str],
) -> Any | None:

    if isinstance(value, dict):

        for key, child in value.items():
            if key.lower() in keys:
                return child

        for child in value.values():
            result = _recursive_find_key(child, keys)

            if result is not None:
                return result

    elif isinstance(value, list):

        for child in value:
            result = _recursive_find_key(child, keys)

            if result is not None:
                return result

    return None


def _number(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):

        match = re.search(
            r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
            r"(?:[eE][-+]?\d+)?",
            value,
        )

        if match:
            try:
                return float(match.group(0))
            except ValueError:
                pass

    return None


def _extract_elements(data: dict[str, Any]) -> dict[str, Any]:

    # Find_Orb's JSON schema can evolve. Instead of assuming one
    # exact nesting layout, search common element names recursively.

    aliases = {
        "a": {"a", "semimajoraxis", "semi_major_axis"},
        "e": {"e", "eccentricity"},
        "i": {"i", "inclination"},
        "q": {"q", "perihelion", "periheliondistance"},
        "om": {"om", "omega", "argumentofperihelion"},
        "node": {
            "omnode",
            "longitudeofascendingnode",
            "ascendingnode",
            "node",
        },
        "M": {"m", "meananomaly"},
        "tp": {"tp", "timeofperihelion"},
        "epoch": {"epoch", "epochjd", "jd"},
        "moid": {"moid"},
        "h": {"h", "absolutemagnitude"},
    }

    result: dict[str, Any] = {}

    for output_key, keyset in aliases.items():

        raw = _recursive_find_key(data, keyset)

        value = _number(raw)

        if value is not None:
            result[output_key] = value

    return result


def _derive_elements(elements: dict[str, Any]) -> dict[str, Any]:

    a = elements.get("a")
    e = elements.get("e")

    if a is not None:

        if e is not None:
            elements.setdefault(
                "perihelion_au",
                a * (1.0 - e),
            )

            elements.setdefault(
                "aphelion_au",
                a * (1.0 + e),
            )

        if a > 0:

            period_years = math.sqrt(a ** 3)

            elements.setdefault(
                "period_years",
                period_years,
            )

            elements.setdefault(
                "period_days",
                period_years * 365.2568983,
            )

    return elements


def _orbit_point(
    a: float,
    e: float,
    inclination_deg: float,
    node_deg: float,
    arg_peri_deg: float,
    true_anomaly_deg: float,
) -> list[float]:

    nu = math.radians(true_anomaly_deg)

    inclination = math.radians(inclination_deg)
    node = math.radians(node_deg)
    arg_peri = math.radians(arg_peri_deg)

    denominator = 1.0 + e * math.cos(nu)

    if abs(denominator) < 1e-12:
        denominator = 1e-12

    radius = a * (1.0 - e * e) / denominator

    x_orb = radius * math.cos(nu)
    y_orb = radius * math.sin(nu)

    cos_o = math.cos(node)
    sin_o = math.sin(node)

    cos_i = math.cos(inclination)
    sin_i = math.sin(inclination)

    cos_w = math.cos(arg_peri)
    sin_w = math.sin(arg_peri)

    x = (
        (cos_o * cos_w - sin_o * sin_w * cos_i)
        * x_orb
        +
        (-cos_o * sin_w - sin_o * cos_w * cos_i)
        * y_orb
    )

    y = (
        (sin_o * cos_w + cos_o * sin_w * cos_i)
        * x_orb
        +
        (-sin_o * sin_w + cos_o * cos_w * cos_i)
        * y_orb
    )

    z = (
        sin_w * sin_i * x_orb
        +
        cos_w * sin_i * y_orb
    )

    return [x, y, z]


def generate_orbit_path(
    elements: dict[str, Any],
    samples: int = 360,
) -> list[list[float]]:

    a = elements.get("a")
    e = elements.get("e", 0.0)

    inclination = elements.get("i", 0.0)
    node = elements.get("node", 0.0)
    arg_peri = elements.get("om", 0.0)

    if a is None:
        return []

    if e is None:
        e = 0.0

    # Elliptic visualisation only for the first simulator.
    if a <= 0 or e >= 1:
        return []

    points = []

    for index in range(samples):

        anomaly = (
            index / (samples - 1)
        ) * 360.0

        points.append(
            _orbit_point(
                a=a,
                e=e,
                inclination_deg=inclination,
                node_deg=node,
                arg_peri_deg=arg_peri,
                true_anomaly_deg=anomaly,
            )
        )

    return points


def solve_orbit(
    object_name: str,
    observations: list[Any],
) -> dict[str, Any]:

    _require_find_orb()

    if len(observations) < 3:
        raise ValueError(
            "At least three observations are required."
        )

    with tempfile.TemporaryDirectory(
        prefix="orbit-intelligence-"
    ) as temp_dir:

        work_dir = Path(temp_dir)

        input_file = work_dir / "observations.txt"

        lines = [
            _format_observation(
                object_name=object_name,
                time_utc=obs.time_utc,
                ra_deg=obs.ra_deg,
                dec_deg=obs.dec_deg,
                magnitude=obs.magnitude,
            )
            for obs in observations
        ]

        input_file.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

        output = _run_find_orb(
            input_file=input_file,
            output_dir=work_dir,
        )

        try:
            raw_json = _load_best_find_orb_json(work_dir)
            elements = _extract_elements(raw_json)
        except RuntimeError:
            # If JSON was not emitted by the installed configuration,
            # return the raw console output so the integration can be
            # diagnosed rather than silently inventing an orbit.
            raise RuntimeError(
                "Find_Orb ran but the simulator could not locate "
                "a machine-readable orbital solution.\n\n"
                "Find_Orb output:\n"
                + output[-6000:]
            )

        elements = _derive_elements(elements)

        orbit_path = generate_orbit_path(elements)

        return {
            "engine": "Bill Gray Find_Orb",
            "object_name": object_name,
            "observation_count": len(observations),
            "elements": elements,
            "orbit_path_au": orbit_path,
            "raw_output_tail": output[-3000:],
        }
