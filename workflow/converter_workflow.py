"""
YouTube Converter Workflow.

Validates URL (YouTube / YouTube Music, video or playlist), downloads as MP3 or MP4,
and for playlists zips the files. Returns a download link for the single file or zip.
"""

from __future__ import annotations

from app.converter_config import get_job_dir
from workflow.nodes.converter import (
    ConverterState,
    input_validate_node,
    download_node,
    zip_node,
)


def run_converter_workflow(url: str, format: str) -> dict:
    """
    Run the converter workflow: validate -> download -> zip (if multiple) -> return.
    format must be "mp3" or "mp4".
    Returns dict with status, download_path (relative for URL), error message if failed.
    """
    print("[Converter Workflow] ---------- Converter workflow started ----------")
    state: ConverterState = {
        "url": url,
        "format": format,
        "job_id": None,
        "output_dir": None,
        "downloaded_files": [],
        "zip_path": None,
        "download_filename": None,
        "step": "started",
        "error": None,
    }

    state = input_validate_node(state)
    if state.get("step") == "validation_failed":
        return {
            "status": "validation_failed",
            "error": state.get("error", "Invalid input."),
            "download_path": None,
        }

    job_id, job_dir = get_job_dir()
    state["job_id"] = job_id
    state["output_dir"] = str(job_dir)
    print("[Converter Workflow] Job id: " + job_id)

    state = download_node(state)
    if state.get("step") == "download_failed":
        return {
            "status": "download_failed",
            "error": state.get("error", "Download failed."),
            "download_path": None,
        }

    state = zip_node(state)
    if state.get("step") == "zip_failed":
        return {
            "status": "zip_failed",
            "error": state.get("error", "Zip failed."),
            "download_path": None,
        }

    download_path = state.get("download_filename")
    print("[Converter Workflow] Workflow complete. Download path: " + str(download_path))
    return {
        "status": "completed",
        "download_path": download_path,
        "job_id": job_id,
        "error": None,
    }
