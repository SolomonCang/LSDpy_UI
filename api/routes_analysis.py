"""Analysis routes for the LSD UI API.

Provides POST /api/analysis — run the LSD basic analysis framework on a
saved profile file (profile analysis, RV fitting, noise test, Bl field).

Call init(base_dir) from app.py before including this router so that
relative profile paths are resolved correctly.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException

from core.lsd_analysis import analyze_profile

router = APIRouter()
logger = logging.getLogger(__name__)

_BASE_DIR: Path = Path(".")


def init(base_dir: Path):
    """Register the project root so relative profile paths can be resolved."""
    global _BASE_DIR
    _BASE_DIR = Path(base_dir).resolve()


def _resolve_safe_path(relative: str) -> Path:
    """Resolve *relative* against BASE_DIR and reject path-traversal attempts.

    Raises HTTPException(400) if the resolved path escapes BASE_DIR.
    """
    candidate = (_BASE_DIR / relative).resolve()
    try:
        candidate.relative_to(_BASE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid profile_file path: must be relative to the results directory.",
        )
    return candidate


@router.post("/api/analysis")
def run_analysis(body: dict = Body(...)):
    """Run LSD basic analysis on a saved LSD profile file.

    Request body (JSON):
      profile_file  string   Path to the profile .dat file, relative to BASE_DIR.
      norm_wave     number   Normalisation wavelength in nm  (default 500.0).
      norm_lande    number   Effective Landé g-factor         (default 1.2).

    Response (JSON):
      profile        dict  Profile statistics (depth, EW, centroid, FWHM, SNR).
      rv_fit         dict  Gaussian RV fit results.
      noise          dict  Null-test chi², FAP, and detection labels for V and N1.
      magnetic_field dict  Bl result — present only when Stokes V data are available.
    """
    profile_file = body.get("profile_file", "").strip()
    if not profile_file:
        raise HTTPException(status_code=400, detail="profile_file is required")

    try:
        norm_wave = float(body.get("norm_wave", 500.0))
        norm_lande = float(body.get("norm_lande", 1.2))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {exc}")

    abs_path = _resolve_safe_path(profile_file)
    if not abs_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Profile file not found: {profile_file}",
        )

    try:
        result = analyze_profile(
            str(abs_path),
            norm_wave_nm=norm_wave,
            norm_lande=norm_lande,
        )
        return result
    except Exception as exc:
        logger.exception("Analysis failed for %s", profile_file)
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Check server logs for details.",
        ) from exc
