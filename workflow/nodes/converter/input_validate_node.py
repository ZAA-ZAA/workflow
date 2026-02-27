"""Validate YouTube/YT Music URL and format (mp3 or mp4)."""

import re

from .state import ConverterState

# Supported URL patterns (YouTube, YouTube Music, youtu.be)
YT_PATTERNS = (
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/",
    r"^https?://(www\.)?youtube\.com/watch\?v=",
    r"^https?://(www\.)?youtube\.com/playlist\?list=",
    r"^https?://music\.youtube\.com/watch\?v=",
    r"^https?://music\.youtube\.com/playlist\?list=",
    r"^https?://youtu\.be/",
)


def input_validate_node(state: ConverterState) -> ConverterState:
    """
    Validate URL (YouTube/YT Music, video or playlist) and format (mp3 or mp4).
    """
    url = (state.get("url") or "").strip()
    fmt = (state.get("format") or "").strip().lower()

    if not url:
        print("[Converter Workflow] Step: validation_failed (missing url)")
        return {
            **state,
            "step": "validation_failed",
            "error": "Missing URL.",
        }

    if fmt not in ("mp3", "mp4"):
        print("[Converter Workflow] Step: validation_failed (invalid format)")
        return {
            **state,
            "step": "validation_failed",
            "error": "Format must be mp3 or mp4.",
        }

    # Normalize URL: ensure scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    matched = any(re.search(p, url, re.IGNORECASE) for p in YT_PATTERNS)
    if not matched:
        # Also allow any youtube / youtu.be / music.youtube host
        if "youtube.com" in url or "youtu.be" in url or "music.youtube.com" in url:
            matched = True
    if not matched:
        print("[Converter Workflow] Step: validation_failed (invalid url)")
        return {
            **state,
            "step": "validation_failed",
            "error": "URL must be a YouTube or YouTube Music link (video or playlist).",
        }

    print("[Converter Workflow] Step: validated (url=" + url[:60] + "... format=" + fmt + ")")
    return {
        **state,
        "url": url,
        "format": fmt,
        "step": "validated",
        "error": None,
    }
