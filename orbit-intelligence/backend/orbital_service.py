from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent

FO_BINARY = BASE_DIR / "bin" / "fo"
FO_CONFIG_DIR = BASE_DIR / "findorb-data"

ENVIRON_DEF = FO_CONFIG_DIR / "environ.def"
COSPAR_FILE = FO_CONFIG_DIR / "cospar.txt"
DE430_FILE = FO_CONFIG_DIR / "linux_p1550p2650.430t"

GAUSSIAN_K = 0.01720209895


def _require_find_orb() -> None:
    """
    Verify that Find_Orb and its runtime data were installed
    by render-build.sh.
    """

    if not FO_BINARY.exists():
        raise RuntimeError(
            f"Find_Orb executable not found: {FO_BINARY}"
        )

    if not FO_BINARY.is_file():
        raise RuntimeError(
            f"Find_Orb path is not a file: {FO_BINARY}"
        )

    try:
        size = FO_BINARY.stat().st_size
    except OSError as exc:
        raise RuntimeError(
            f"Cannot inspect Find_Orb executable: {exc}"
        ) from exc

    if size < 1024:
        raise RuntimeError(
            f"Find_Orb executable is suspiciously small: "
            f"{size} bytes"
        )

    if not os.access(FO_BINARY, os.X_OK):
        raise RuntimeError(
            f"Find_Orb executable is not executable: {FO_BINARY}"
        )

    if not FO_CONFIG_DIR.exists():
        raise RuntimeError(
            f"Find_Orb configuration directory is missing: "
            f"{FO_CONFIG_DIR}"
        )

    if not ENVIRON_DEF.exists():
        raise RuntimeError(
            f"Find_Orb environment file is missing: "
            f"{ENVIRON_DEF}"
        )

    if not COSPAR_FILE.exists():
        raise RuntimeError(
            f"Find_Orb COSPAR file is missing: "
            f"{COSPAR_FILE}"
        )

    if not DE430_FILE.exists():
        raise RuntimeError(
            f"Find_Orb DE430 ephemeris is missing: "
            f"{DE430_FILE}"
        )


def _decimal_to_ra(
    ra_deg: float,
) -> tuple[int, int, float]:
    """
    Convert right ascension from decimal degrees
    to hours, minutes and seconds.
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

    if seconds >= 59.9995:
        seconds = 0.0
        minutes += 1

    if minutes >= 60:
        minutes = 0
        hours += 1

    hours %= 24

    return (
        hours,
        minutes,
        seconds,
    )


def _decimal_to_dec(
    dec_deg: float,
) -> tuple[str, int, int, float]:
    """
    Convert declination from decimal degrees
    to sign, degrees, arcminutes and arcseconds.
    """

    sign = "+" if dec_deg >= 0.0 else "-"

    value = abs(dec_deg)

    degrees = int(value)

    minutes_total = (
        value - degrees
    ) * 60.0

    minutes = int(minutes_total)

    seconds = (
        minutes_total - minutes
    ) * 60.0

    if seconds >= 59.95:
        seconds = 0.0
        minutes += 1

    if minutes >= 60:
        minutes = 0
        degrees += 1

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
    Convert an ISO UTC timestamp into MPC-style
    year/month/day fractional date.

    Example:

        2026-09-17T12:30:00Z

    becomes:

        2026 09 17.520833
    """

    value = (
        time_utc
        .strip()
    )

    if value.endswith("Z"):
        value = value[:-1]

    if "+" in value:
        value = value.split(
            "+",
            1,
        )[0]

    if "T" not in value:
        raise ValueError(
            f"Invalid UTC timestamp: {time_utc}"
        )

    date_part, time_part = value.split(
        "T",
        1,
    )

    date_parts = date_part.split("-")

    if len(date_parts) != 3:
        raise ValueError(
            f"Invalid UTC date: {time_utc}"
        )

    try:
        year = int(date_parts[0])
        month = int(date_parts[1])
        day = int(date_parts[2])
    except ValueError as exc:
        raise ValueError(
            f"Invalid UTC date: {time_utc}"
        ) from exc

    time_parts = time_part.split(":")

    if len(time_parts) != 3:
        raise ValueError(
            f"Invalid UTC time: {time_utc}"
        )

    try:
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = float(time_parts[2])
    except ValueError as exc:
        raise ValueError(
            f"Invalid UTC time: {time_utc}"
        ) from exc

    if not 0 <= hour <= 23:
        raise ValueError(
            f"Invalid UTC hour: {time_utc}"
        )

    if not 0 <= minute <= 59:
        raise ValueError(
            f"Invalid UTC minute: {time_utc}"
        )

    if not 0.0 <= second < 60.0:
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
    Create an MPC 80-column optical observation.

    Observatory code 500 is the geocenter.
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

    line = (
        f"{object_name[:12]:<12}"
        f"C"
        f"{date_string:>17}"
        f" "
        f"{ra_h:02d} "
        f"{ra_m:02d} "
        f"{ra_s:05.2f}"
        f" "
        f"{dec_sign}"
        f"{dec_d:02d} "
        f"{dec_m:02d} "
        f"{dec_s:04.1f}"
    )

    if magnitude is not None:
        line += (
            f"     "
            f"{magnitude:4.1f}"
        )
    else:
        line += "         "

    line += "     500"

    return line[:80]


def _prepare_runtime_home(
    output_dir: Path,
) -> Path:
    """
    Create a temporary HOME for Find_Orb.

    Find_Orb stores its mutable environment settings
    separately from the immutable packaged defaults.

    We copy environ.def into the temporary HOME so that
    the default-environment lookup always has a valid file.
    """

    home_dir = (
        output_dir
        / "findorb-home"
    )

    home_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        ENVIRON_DEF,
        home_dir / "environ.def",
    )

    return home_dir


def _run_find_orb(
    input_file: Path,
    output_dir: Path,
) -> str:
    """
    Execute the non-interactive Find_Orb program.

    Important Find_Orb switches:

        -x <directory>
            alternate configuration directory

        -D <file>
            explicit environment file

        -q
            quiet processing

        -O <directory>
            output directory

    We deliberately do NOT use '-v' because Find_Orb uses
    '-v' for state-vector input.
    """

    _require_find_orb()

    config_dir_argument = str(
        FO_CONFIG_DIR
    )

    if not config_dir_argument.endswith(
        os.sep
    ):
        config_dir_argument += os.sep

    runtime_home = _prepare_runtime_home(
        output_dir
    )

    runtime_environment_file = (
        runtime_home
        / "environ.def"
    )

    command = [
        str(FO_BINARY),

        "-x",
        config_dir_argument,

        "-D",
        str(runtime_environment_file),

        "-O",
        str(output_dir),

        "-q",

        str(input_file),
    ]

    env = os.environ.copy()

    env["HOME"] = str(
        runtime_home
    )

    env["FIND_ORB_HOME"] = str(
        runtime_home
    )

    try:
        process = subprocess.run(
            command,
            cwd=output_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Find_Orb exceeded the 60-second execution limit."
        ) from exc

    except OSError as exc:
        raise RuntimeError(
            f"Could not execute Find_Orb: {exc}"
        ) from exc

    stdout = process.stdout or ""
    stderr = process.stderr or ""

    combined_output = (
        stdout
        + "\n"
        + stderr
    )

    if process.returncode != 0:
        raise RuntimeError(
            "Find_Orb failed.\n\n"
            + combined_output[-8000:]
        )

    return combined_output


def _find_json_files(
    directory: Path,
) -> list[Path]:
    """
    Locate JSON files produced by Find_Orb.
    """

    return sorted(
        directory.rglob("*.json"),
        key=lambda path: path.stat().st_mtime
        if path.exists()
        else 0.0,
        reverse=True,
    )


def _load_json_file(
    path: Path,
) -> dict[str, Any] | None:
    """
    Load a JSON object safely.
    """

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if isinstance(
        data,
        dict,
    ):
        return data

    return None


def _load_best_find_orb_json(
    directory: Path,
) -> dict[str, Any]:
    """
    Load the best available Find_Orb JSON result.

    The non-interactive Find_Orb executable creates
    total.json and per-object element JSON products.
    """

    candidates = (
        _find_json_files(
            directory
        )
    )

    if not candidates:
        raise RuntimeError(
            "Find_Orb completed but produced no JSON files."
        )

    preferred_names = (
        "elements.json",
        "total.json",
    )

    ordered: list[Path] = []

    for preferred_name in preferred_names:
        for candidate in candidates:
            if (
                candidate.name.lower()
                == preferred_name
            ):
                ordered.append(
                    candidate
                )

    for candidate in candidates:
        if candidate not in ordered:
            ordered.append(
                candidate
            )

    for candidate in ordered:

        data = _load_json_file(
            candidate
        )

        if data is not None:
            return data

    raise RuntimeError(
        "Find_Orb produced JSON files, "
        "but none could be parsed."
    )


def _normalise_key(
    key: Any,
) -> str:
    """
    Normalise a JSON key for flexible matching.
    """

    return (
        str(key)
        .lower()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )


def _recursive_find_key(
    value: Any,
    keys: set[str],
) -> Any | None:
    """
    Recursively find the first matching JSON key.
    """

    if isinstance(
        value,
        dict,
    ):

        for key, child in value.items():

            if (
                _normalise_key(key)
                in keys
            ):
                return child

        for child in value.values():

            result = _recursive_find_key(
                child,
                keys,
            )

            if result is not None:
                return result

    elif isinstance(
        value,
        list,
    ):

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
    Convert a JSON value into a floating-point number.
    """

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    if isinstance(
        value,
        (int, float),
    ):
        return float(value)

    if isinstance(
        value,
        str,
    ):

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
                return None

    return None


def _extract_elements(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract common orbital elements from Find_Orb JSON.

    The parser supports multiple possible JSON key names.
    """

    aliases: dict[str, set[str]] = {

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

        "om": {
            "om",
            "omega",
            "argumentofperihelion",
            "argumentofperiheliondeg",
        },

        "node": {
            "node",
            "ascendingnode",
            "longitudeofascendingnode",
            "longitudeofascendingnodedeg",
        },

        "M": {
            "m",
            "meananomaly",
            "meananomalydeg",
        },

        "q": {
            "q",
            "perihelion",
            "periheliondistance",
            "periheliondistanceau",
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

        raw = _recursive_find_key(
            data,
            keyset,
        )

        value = _number(
            raw
        )

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

    if (
        a is not None
        and e is not None
    ):

        elements.setdefault(
            "perihelion_au",
            a * (1.0 - e),
        )

        elements.setdefault(
            "aphelion_au",
            a * (1.0 + e),
        )

    if (
        a is not None
        and a > 0.0
    ):

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
    Convert Keplerian orbital elements into
    heliocentric Cartesian AU.
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
    Generate a 3D orbital path for the frontend.

    The visualiser currently supports elliptic
    heliocentric solutions.
    """

    a = _number(
        elements.get("a")
    )

    e = _number(
        elements.get("e")
    )

    inclination = _number(
        elements.get("i")
    )

    node = _number(
        elements.get("node")
    )

    arg_peri = _number(
        elements.get("om")
    )

    if a is None:
        return []

    if e is None:
        e = 0.0

    if inclination is None:
        inclination = 0.0

    if node is None:
        node = 0.0

    if arg_peri is None:
        arg_peri = 0.0

    if (
        a <= 0.0
        or e < 0.0
        or e >= 1.0
    ):
        return []

    if samples < 2:
        samples = 2

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
    Complete orbit-determination pipeline.

    1. Validate Find_Orb installation.
    2. Convert observations to MPC format.
    3. Execute Find_Orb.
    4. Read its JSON orbital solution.
    5. Extract orbital elements.
    6. Generate a 3D orbit path.
    """

    _require_find_orb()

    if len(observations) < 3:
        raise ValueError(
            "At least three observations are required."
        )

    object_name = (
        object_name
        .strip()
    )

    if not object_name:
        raise ValueError(
            "Object name cannot be empty."
        )

    with tempfile.TemporaryDirectory(
        prefix="orbit-intelligence-"
    ) as temp_dir:

        work_dir = Path(
            temp_dir
        )

        input_file = (
            work_dir
            / "observations.txt"
        )

        lines: list[str] = []

        for observation in observations:

            lines.append(
                _format_observation(
                    object_name=object_name,
                    time_utc=observation.time_utc,
                    ra_deg=observation.ra_deg,
                    dec_deg=observation.dec_deg,
                    magnitude=observation.magnitude,
                )
            )

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

        except RuntimeError as exc:

            generated_files = sorted(
                str(
                    path.relative_to(
                        work_dir
                    )
                )
                for path in work_dir.rglob("*")
                if path.is_file()
            )

            raise RuntimeError(
                str(exc)
                + "\n\n"
                + "Find_Orb output:\n"
                + output[-6000:]
                + "\n\n"
                + "Generated files:\n"
                + "\n".join(
                    generated_files
                )
            ) from exc

        elements = _extract_elements(
            raw_json
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
            "engine": "Bill Gray Find_Orb",

            "object_name": object_name,

            "observation_count": len(
                observations
            ),

            "elements": elements,

            "orbit_path_au": orbit_path,

            "raw_output_tail": output[
                -3000:
            ],
        }
