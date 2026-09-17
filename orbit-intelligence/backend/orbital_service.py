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
# AU^(3/2) / day.
GAUSSIAN_K = 0.01720209895


def _require_find_orb() -> None:
    """
    Verify that the Find_Orb executable and its runtime
    configuration are available.
    """

    if not FO_BINARY.exists():
        raise RuntimeError(
            f"Find_Orb executable not found at {FO_BINARY}. "
            "The Render build may have failed to install 'fo'."
        )

    if not os.access(FO_BINARY, os.X_OK):
        raise RuntimeError(
            f"Find_Orb exists but is not executable: {FO_BINARY}"
        )

    if not FO_CONFIG_DIR.exists():
        raise RuntimeError(
            f"Find_Orb configuration directory not found at "
            f"{FO_CONFIG_DIR}."
        )

    cospar_file = FO_CONFIG_DIR / "cospar.txt"

    if not cospar_file.exists():
        raise RuntimeError(
            "Find_Orb configuration is incomplete. "
            f"Missing required file: {cospar_file}"
        )


def _decimal_to_ra(
    ra_deg: float,
) -> tuple[int, int, float]:
    """
    Convert decimal-degree right ascension into
    hours, minutes, seconds.
    """

    total_hours = ra_deg / 15.0

    hours = int(total_hours)

    minutes_total = (
        total_hours - hours
    ) * 60.0

    minutes = int(minutes_total)

    seconds = (
        minutes_total - minutes
    ) * 60.0

    return hours, minutes, seconds


def _decimal_to_dec(
    dec_deg: float,
) -> tuple[str, int, int, float]:
    """
    Convert decimal-degree declination into
    sign, degrees, arcminutes, arcseconds.
    """

    sign = "+" if dec_deg >= 0 else "-"

    value = abs(dec_deg)

    degrees = int(value)

    minutes_total = (
        value - degrees
    ) * 60.0

    minutes = int(minutes_total)

    seconds = (
        minutes_total - minutes
    ) * 60.0

    return (
        sign,
        degrees,
        minutes,
        seconds,
    )


def _format_mpc_date(
    time_utc: str,
) -> str:
    """
    Convert an ISO-ish UTC timestamp to MPC-style:

        YYYY MM DD.dddddd

    Example:

        2026-09-17T12:30:00Z

    becomes approximately:

        2026 09 17.520833
    """

    value = (
        time_utc
        .strip()
        .replace("Z", "")
    )

    if "T" not in value:
        raise ValueError(
            f"Invalid UTC timestamp: {time_utc}"
        )

    date_part, time_part = value.split(
        "T",
        1,
    )

    try:
        year, month, day = [
            int(x)
            for x in date_part.split("-")
        ]
    except ValueError as exc:
        raise ValueError(
            f"Invalid UTC date: {time_utc}"
        ) from exc

    time_part = (
        time_part
        .split("+")[0]
        .split("-")[0]
    )

    parts = time_part.split(":")

    if len(parts) != 3:
        raise ValueError(
            f"Invalid UTC time: {time_utc}"
        )

    hour = int(parts[0])
    minute = int(parts[1])
    second = float(parts[2])

    if not 0 <= hour <= 23:
        raise ValueError(
            f"Invalid UTC hour: {time_utc}"
        )

    if not 0 <= minute <= 59:
        raise ValueError(
            f"Invalid UTC minute: {time_utc}"
        )

    if not 0 <= second < 60:
        raise ValueError(
            f"Invalid UTC second: {time_utc}"
        )

    day_fraction = (
        hour / 24.0
        + minute / 1440.0
        + second / 86400.0
    )

    return (
        f"{year:04d} "
        f"{month:02d} "
        f"{day + day_fraction:09.6f}"
    )


def _format_observation(
    object_name: str,
    time_utc: str,
    ra_deg: float,
    dec_deg: float,
    magnitude: float | None,
) -> str:
    """
    Format an observation as an MPC-style
    optical observation line.

    The current simulator uses synthetic
    geocentric observatory code 500.
    """

    (
        ra_h,
        ra_m,
        ra_s,
    ) = _decimal_to_ra(
        ra_deg
    )

    (
        dec_sign,
        dec_d,
        dec_m,
        dec_s,
    ) = _decimal_to_dec(
        dec_deg
    )

    date_string = _format_mpc_date(
        time_utc
    )

    if magnitude is not None:
        mag = f"{magnitude:4.1f}"
    else:
        mag = "    "

    line = (
        f"{object_name[:12]:<12}"
        f" C"
        f"{date_string:>17}"
        f" {ra_h:02d}"
        f" {ra_m:02d}"
        f" {ra_s:05.2f}"
        f" {dec_sign}"
        f"{dec_d:02d}"
        f" {dec_m:02d}"
        f" {dec_s:04.1f}"
        f"          "
        f"{mag}"
        f" 500"
    )

    return line[:80]


def _run_find_orb(
    input_file: Path,
    output_dir: Path,
) -> str:
    """
    Run the non-interactive Find_Orb executable.

    Find_Orb requires its configuration files,
    including cospar.txt. The configuration is
    packaged with this application under:

        backend/findorb-data/

    The -x argument explicitly tells Find_Orb
    where that configuration directory is.
    """

    if not FO_CONFIG_DIR.exists():
        raise RuntimeError(
            "Find_Orb configuration directory "
            f"does not exist: {FO_CONFIG_DIR}"
        )

    cospar_file = (
        FO_CONFIG_DIR / "cospar.txt"
    )

    if not cospar_file.exists():
        raise RuntimeError(
            "Find_Orb configuration is missing "
            f"cospar.txt: {cospar_file}"
        )

    command = [
        str(FO_BINARY),
        "-x",
        str(FO_CONFIG_DIR),
        str(input_file),
        "-v",
    ]

    env = os.environ.copy()

    # Find_Orb may generate temporary products.
    # Keep those isolated from the packaged
    # configuration directory.
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
            "Find_Orb exceeded the "
            "45-second execution limit."
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


def _find_json_files(
    directory: Path,
) -> list[Path]:
    """
    Find JSON products generated by Find_Orb.
    """

    return list(
        directory.rglob("*.json")
    )


def _load_best_find_orb_json(
    directory: Path,
) -> dict[str, Any]:
    """
    Load the most likely Find_Orb orbital
    solution JSON file.
    """

    candidates = _find_json_files(
        directory
    )

    preferred = [
        path
        for path in candidates
        if path.name.lower()
        in {
            "total.json",
            "elements.json",
            "short.json",
            "elem_short.json",
        }
    ]

    candidates = (
        preferred
        or candidates
    )

    for path in candidates:
        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data

        except (
            OSError,
            json.JSONDecodeError,
        ):
            continue

    raise RuntimeError(
        "Find_Orb completed but no readable "
        "JSON result was produced."
    )


def _recursive_find_key(
    value: Any,
    keys: set[str],
) -> Any | None:
    """
    Recursively search nested JSON data
    for one of the requested keys.
    """

    if isinstance(value, dict):

        for key, child in value.items():

            normalized = (
                str(key)
                .lower()
                .replace("_", "")
                .replace("-", "")
                .replace(" ", "")
            )

            if normalized in keys:
                return child

        for child in value.values():

            result = _recursive_find_key(
                child,
                keys,
            )

            if result is not None:
                return result

    elif isinstance(value, list):

        for child in value:

            result = _recursive_find_key(
                child,
                keys,
            )

            if result is not None:
                return result

    return None


def _number(
    value: Any,
) -> float | None:
    """
    Convert a JSON value into a float
    when possible.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(
        value,
        (int, float),
    ):
        return float(value)

    if isinstance(value, str):

        match = re.search(
            r"[-+]?(?:"
            r"\d+(?:\.\d*)?"
            r"|"
            r"\.\d+"
            r")"
            r"(?:[eE][-+]?\d+)?",
            value,
        )

        if match:

            try:
                return float(
                    match.group(0)
                )

            except ValueError:
                pass

    return None


def _extract_elements(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract common orbital elements from
    Find_Orb JSON output.

    The parser intentionally searches recursively
    because Find_Orb JSON layouts can change.
    """

    aliases = {
        "a": {
            "a",
            "semimajoraxis",
            "semimajoraxisau",
        },

        "e": {
            "e",
            "eccentricity",
        },

        "i": {
            "i",
            "inclination",
            "inclinationdeg",
        },

        "q": {
            "q",
            "perihelion",
            "periheliondistance",
            "periheliondistanceau",
        },

        "om": {
            "om",
            "omega",
            "argumentofperihelion",
            "argumentofperiheliondeg",
        },

        "node": {
            "omnode",
            "longitudeofascendingnode",
            "ascendingnode",
            "node",
            "nodeangle",
        },

        "M": {
            "m",
            "meananomaly",
            "meananomalydeg",
        },

        "tp": {
            "tp",
            "timeofperihelion",
        },

        "epoch": {
            "epoch",
            "epochjd",
            "jd",
        },

        "moid": {
            "moid",
        },

        "h": {
            "h",
            "absolutemagnitude",
        },
    }

    result: dict[str, Any] = {}

    for output_key, keyset in aliases.items():

        normalized_keyset = {
            key.lower()
            .replace("_", "")
            .replace("-", "")
            .replace(" ", "")
            for key in keyset
        }

        raw = _recursive_find_key(
            data,
            normalized_keyset,
        )

        value = _number(raw)

        if value is not None:
            result[output_key] = value

    return result


def _derive_elements(
    elements: dict[str, Any],
) -> dict[str, Any]:
    """
    Derive useful secondary orbital quantities.
    """

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

            period_years = math.sqrt(
                a ** 3
            )

            elements.setdefault(
                "period_years",
                period_years,
            )

            elements.setdefault(
                "period_days",
                period_years
                * 365.2568983,
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
    """
    Convert a Keplerian orbital position
    into heliocentric Cartesian AU.
    """

    nu = math.radians(
        true_anomaly_deg
    )

    inclination = math.radians(
        inclination_deg
    )

    node = math.radians(
        node_deg
    )

    arg_peri = math.radians(
        arg_peri_deg
    )

    denominator = (
        1.0
        + e * math.cos(nu)
    )

    if abs(denominator) < 1e-12:
        denominator = 1e-12

    radius = (
        a
        * (1.0 - e * e)
        / denominator
    )

    x_orb = (
        radius
        * math.cos(nu)
    )

    y_orb = (
        radius
        * math.sin(nu)
    )

    cos_o = math.cos(node)
    sin_o = math.sin(node)

    cos_i = math.cos(inclination)
    sin_i = math.sin(inclination)

    cos_w = math.cos(arg_peri)
    sin_w = math.sin(arg_peri)

    x = (
        (
            cos_o * cos_w
            - sin_o * sin_w * cos_i
        )
        * x_orb
        +
        (
            -cos_o * sin_w
            - sin_o * cos_w * cos_i
        )
        * y_orb
    )

    y = (
        (
            sin_o * cos_w
            + cos_o * sin_w * cos_i
        )
        * x_orb
        +
        (
            -sin_o * sin_w
            + cos_o * cos_w * cos_i
        )
        * y_orb
    )

    z = (
        sin_w * sin_i * x_orb
        +
        cos_w * sin_i * y_orb
    )

    return [
        x,
        y,
        z,
    ]


def generate_orbit_path(
    elements: dict[str, Any],
    samples: int = 360,
) -> list[list[float]]:
    """
    Generate a visual orbit path for the frontend.
    """

    a = elements.get("a")

    e = elements.get(
        "e",
        0.0,
    )

    inclination = elements.get(
        "i",
        0.0,
    )

    node = elements.get(
        "node",
        0.0,
    )

    arg_peri = elements.get(
        "om",
        0.0,
    )

    if a is None:
        return []

    if e is None:
        e = 0.0

    # Current visualiser supports
    # elliptic orbits only.
    if a <= 0 or e >= 1:
        return []

    points: list[list[float]] = []

    for index in range(samples):

        anomaly = (
            index
            / (samples - 1)
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
    """
    Main orbit-determination pipeline.

    1. Validate Find_Orb installation.
    2. Convert frontend observations into
       MPC-style optical observations.
    3. Execute Bill Gray's Find_Orb.
    4. Locate its JSON orbital solution.
    5. Extract orbital elements.
    6. Generate a 3D visualisation path.
    """

    _require_find_orb()

    if len(observations) < 3:
        raise ValueError(
            "At least three observations "
            "are required."
        )

    with tempfile.TemporaryDirectory(
        prefix="orbit-intelligence-"
    ) as temp_dir:

        work_dir = Path(temp_dir)

        input_file = (
            work_dir
            / "observations.txt"
        )

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
            "\n".join(lines)
            + "\n",
            encoding="utf-8",
        )

        output = _run_find_orb(
            input_file=input_file,
            output_dir=work_dir,
        )

        try:

            raw_json = (
                _load_best_find_orb_json(
                    work_dir
                )
            )

            elements = (
                _extract_elements(
                    raw_json
                )
            )

        except RuntimeError:

            raise RuntimeError(
                "Find_Orb ran but the simulator "
                "could not locate a machine-readable "
                "orbital solution.\n\n"
                "Find_Orb output:\n"
                + output[-6000:]
            )

        elements = _derive_elements(
            elements
        )

        orbit_path = (
            generate_orbit_path(
                elements
            )
        )

        return {
            "engine": (
                "Bill Gray Find_Orb"
            ),

            "object_name": (
                object_name
            ),

            "observation_count": (
                len(observations)
            ),

            "elements": (
                elements
            ),

            "orbit_path_au": (
                orbit_path
            ),

            "raw_output_tail": (
                output[-3000:]
            ),
        }
