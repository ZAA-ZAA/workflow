"""State definition for YouTube converter workflow."""

from typing import Optional, TypedDict


class ConverterState(TypedDict):
    """State passed between converter nodes."""

    url: str
    format: str  # "mp3" | "mp4"
    job_id: Optional[str]
    output_dir: Optional[str]
    downloaded_files: list[str]
    zip_path: Optional[str]
    download_filename: Optional[str]  # single file or zip for response
    step: str
    error: Optional[str]
