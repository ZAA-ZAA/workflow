"""Zip multiple downloaded files into one archive for playlist results."""

from __future__ import annotations

import zipfile
from pathlib import Path

from .state import ConverterState


def zip_node(state: ConverterState) -> ConverterState:
    """
    If multiple files: create a zip in output_dir named job_id.zip and set
    download_filename to that zip. If single file: set download_filename to that file.
    """
    output_dir = state.get("output_dir")
    job_id = state.get("job_id")
    files = state.get("downloaded_files") or []

    if not output_dir or not files:
        return {**state, "step": "zip_failed", "error": "No files to zip."}

    output_path = Path(output_dir)
    if len(files) == 1:
        single = Path(files[0])
        if single.is_file():
            # Return relative path for download URL: job_id/filename
            rel = single.name
            print("[Converter Workflow] Step: single file ready - " + rel)
            return {
                **state,
                "download_filename": f"{job_id}/{rel}",
                "zip_path": None,
                "step": "completed",
                "error": None,
            }
        return {**state, "step": "zip_failed", "error": "Downloaded file not found."}

    zip_name = f"{job_id}.zip"
    zip_path = output_path / zip_name
    print("[Converter Workflow] Step: zipping " + str(len(files)) + " files into " + zip_name)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                p = Path(f)
                if p.is_file():
                    zf.write(p, p.name)
        if not zip_path.is_file():
            return {**state, "step": "zip_failed", "error": "Zip file was not created."}
        print("[Converter Workflow] Step: completed (zip ready)")
        return {
            **state,
            "download_filename": f"{job_id}/{zip_name}",
            "zip_path": str(zip_path),
            "step": "completed",
            "error": None,
        }
    except Exception as e:
        return {
            **state,
            "step": "zip_failed",
            "error": "Zip failed: " + str(e)[:200],
        }
