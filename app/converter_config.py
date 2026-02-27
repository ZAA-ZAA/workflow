"""
Config and paths for the YouTube converter workflow.
Output is stored under CONVERTER_OUTPUT_DIR; each job gets a subdir by job_id.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

CONVERTER_OUTPUT_DIR = Path(
    os.getenv("CONVERTER_OUTPUT_DIR", Path(__file__).resolve().parent.parent.parent / "data" / "converter_output")
)
if isinstance(CONVERTER_OUTPUT_DIR, str):
    CONVERTER_OUTPUT_DIR = Path(CONVERTER_OUTPUT_DIR)
CONVERTER_OUTPUT_DIR = CONVERTER_OUTPUT_DIR.resolve()


def get_job_dir() -> tuple[str, Path]:
    """Return (job_id, absolute Path to job output dir). Job dir is created."""
    job_id = str(uuid.uuid4())[:8]
    job_dir = CONVERTER_OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_id, job_dir


def safe_download_path(requested: str) -> Path | None:
    """
    Resolve requested filename to a path under CONVERTER_OUTPUT_DIR.
    Returns None if path would escape (security). Only allow basename or job_id/basename.
    """
    requested = (requested or "").strip()
    if not requested or ".." in requested or requested.startswith("/"):
        return None
    parts = [p for p in requested.split("/") if p]
    if not parts:
        return None
    resolved = CONVERTER_OUTPUT_DIR
    for p in parts:
        if p in (".", "..") or ".." in p:
            return None
        resolved = resolved / p
    try:
        resolved = resolved.resolve()
        if not str(resolved).startswith(str(CONVERTER_OUTPUT_DIR)):
            return None
    except Exception:
        return None
    return resolved if resolved.is_file() else None
