import hashlib
import math
import re
from datetime import datetime, timezone

CLEAN_HEADER = ("source_line", "user_id", "ts_utc", "lat", "lon", "location_id")
MAX_INT64 = (1 << 63) - 1
RULE_VERSION = "1.1"
REASONS = ("BAD_STRUCT", "BAD_ID", "BAD_TIME", "BAD_COORD", "ZERO_COORD", "DUPLICATE")

ID_FORMAT = re.compile(r"[0-9]+")
UTC_FORMAT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


def parse_id(value: str) -> int:
    if ID_FORMAT.fullmatch(value) is None:
        raise ValueError("ID must be a non-negative decimal integer")
    number = int(value)
    if number > MAX_INT64:
        raise ValueError("ID exceeds int64")
    return number


def parse_utc(value: str) -> datetime:
    if UTC_FORMAT.fullmatch(value) is None:
        raise ValueError("Expected UTC time in YYYY-MM-DDTHH:MM:SSZ format")
    return datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)


def parse_coords(latitude: str, longitude: str) -> tuple[float, float]:
    lat, lon = float(latitude), float(longitude)
    if not (math.isfinite(lat) and math.isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180):
        raise ValueError("Coordinates must be finite and within WGS 84 bounds")
    return lat, lon


def sha256_file(path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()
