import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit

_TRACKING_QUERY_PREFIXES = ("utm_",)
_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}

_ADDRESS_REPLACEMENTS = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "street": "st",
    "avenue": "ave",
    "boulevard": "blvd",
    "road": "rd",
    "drive": "dr",
    "lane": "ln",
    "court": "ct",
    "highway": "hwy",
}


def canonicalize_url(value: str) -> str:
    raw = value.strip()
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlsplit(candidate)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")

    query_items = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_QUERY_KEYS
        and not key.lower().startswith(_TRACKING_QUERY_PREFIXES)
    ]
    query = urlencode(sorted(query_items))
    canonical = f"{host}{path}"
    return f"{canonical}?{query}" if query else canonical


def normalize_address(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None

    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"\b(?:suite|ste|unit)\s*#?\s*([a-z0-9-]+)", r" unit \1 ", normalized)
    normalized = re.sub(r"#\s*([a-z0-9-]+)", r" unit \1 ", normalized)
    normalized = re.sub(r"[^a-z0-9\s-]", " ", normalized)

    for source, target in _ADDRESS_REPLACEMENTS.items():
        normalized = re.sub(rf"\b{source}\b", target, normalized)

    return " ".join(normalized.split())


def normalize_city(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).lower().split())
