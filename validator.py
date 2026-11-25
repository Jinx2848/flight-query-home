from datetime import datetime
import math
import re

_FLIGHT_ID_RE = re.compile(r"^[A-Za-z0-9]{2,8}$")
_AIRPORT_RE = re.compile(r"^[A-Z]{3}$")
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
_DATETIME_FMT = "%Y-%m-%d %H:%M"


def _parse_strict_datetime(value: str) -> datetime | None:
    if not isinstance(value, str) or not _DATETIME_RE.fullmatch(value):
        return None
    try:
        dt = datetime.strptime(value, _DATETIME_FMT)
    except ValueError:
        return None
    if dt.strftime(_DATETIME_FMT) != value:
        return None
    return dt


def load_airports(path: str) -> set[str]:
    airports: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            airports.add(stripped)
    return airports


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    # 1. WRONG_FIELD_COUNT
    if not isinstance(fields, list) or len(fields) != 6:
        return "WRONG_FIELD_COUNT"

    stripped = [field.strip() if isinstance(field, str) else "" for field in fields]
    flight_id, origin, destination, dep_str, arr_str, price_str = stripped

    # 2. MISSING_FIELD
    if any(val == "" for val in stripped):
        return "MISSING_FIELD"

    # 3. INVALID_FLIGHT_ID
    if not _FLIGHT_ID_RE.fullmatch(flight_id):
        return "INVALID_FLIGHT_ID"

    # 4. INVALID_ORIGIN
    if not _AIRPORT_RE.fullmatch(origin) or origin not in airports:
        return "INVALID_ORIGIN"

    # 5. INVALID_DESTINATION
    if not _AIRPORT_RE.fullmatch(destination) or destination not in airports:
        return "INVALID_DESTINATION"

    # 6. SAME_ORIGIN_DESTINATION
    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"

    # 7. INVALID_DEPARTURE
    dep_dt = _parse_strict_datetime(dep_str)
    if dep_dt is None:
        return "INVALID_DEPARTURE"

    # 8. INVALID_ARRIVAL
    arr_dt = _parse_strict_datetime(arr_str)
    if arr_dt is None:
        return "INVALID_ARRIVAL"

    # 9. ARRIVAL_NOT_AFTER_DEPARTURE
    if arr_dt <= dep_dt:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"

    # 10. INVALID_PRICE
    try:
        price_val = float(price_str)
    except (ValueError, TypeError):
        return "INVALID_PRICE"
    if not math.isfinite(price_val):
        return "INVALID_PRICE"

    # 11. NON_POSITIVE_PRICE
    if price_val <= 0:
        return "NON_POSITIVE_PRICE"

    return None


def to_record(fields: list[str]) -> dict:
    flight_id, origin, destination, dep_str, arr_str, price_str = [
        field.strip() for field in fields
    ]
    return {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "departure_datetime": dep_str,
        "arrival_datetime": arr_str,
        "price": float(price_str),
    }
