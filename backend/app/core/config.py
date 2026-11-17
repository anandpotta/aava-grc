"""Central configuration for the AAVA GRC backend.

The threshold values mirror the ones used by the legacy d3 v3 compliance-map
script so that a map rendered by the new Angular client bands exactly the same
way as the one your team is used to.
"""
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATASET_DIR = DATA_DIR / "datasets"
SEED_DIR = DATA_DIR / "seed"


class Settings:
    app_name: str = "AAVA GRC Intelligence API"
    version: str = "1.0.0"
    api_prefix: str = "/api"

    # CORS – the Angular dev server
    cors_origins: List[str] = [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ]

    # ---- compliance-map similarity bands (legacy parity) -------------------
    # value >= STRONG              -> Strong   (green)
    # PARTIAL <= value < STRONG    -> Partial  (amber)
    # MINIMAL <= value < PARTIAL   -> Minimal  (red)
    # value < MINIMAL              -> treated as unmapped
    THRESHOLD_STRONG: float = 0.75
    THRESHOLD_PARTIAL: float = 0.60
    THRESHOLD_MINIMAL: float = 0.40

    # Placeholder weight used by the legacy script so that an unmapped node in
    # layer N+1 is still laid out in its column. Links at this weight are drawn
    # transparent and are never treated as real coverage.
    PLACEHOLDER_VALUE: float = 0.001

    # Safety valve for very large maps (the bundled large-volume dataset has
    # 1,109 nodes). Drill-down path enumeration is capped at this many rows.
    MAX_DRILL_ROWS: int = 2000


settings = Settings()

BAND_STRONG = "Strong"
BAND_PARTIAL = "Partial"
BAND_MINIMAL = "Minimal"
BAND_UNMAPPED = "Unmapped"

BAND_ORDER = [BAND_STRONG, BAND_PARTIAL, BAND_MINIMAL, BAND_UNMAPPED]


def band_for(value: float) -> str:
    """Return the coverage band for a similarity score."""
    if value is None:
        return BAND_UNMAPPED
    if value >= settings.THRESHOLD_STRONG:
        return BAND_STRONG
    if value >= settings.THRESHOLD_PARTIAL:
        return BAND_PARTIAL
    if value >= settings.THRESHOLD_MINIMAL:
        return BAND_MINIMAL
    return BAND_UNMAPPED
