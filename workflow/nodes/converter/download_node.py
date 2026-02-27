"""Download video(s) or extract audio using yt-dlp."""

from __future__ import annotations

import os
from pathlib import Path

from .state import ConverterState

# Optional: use yt_dlp as library; fallback to subprocess
try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False


def download_node(state: ConverterState) -> ConverterState:
    """
    Run yt-dlp: for mp3 extract audio; for mp4 download best video+audio.
    Output to state["output_dir"]; fills state["downloaded_files"].
    """
    if not HAS_YT_DLP:
        print("[Converter Workflow] ERROR: yt-dlp not installed. pip install yt-dlp")
        return {
            **state,
            "step": "download_failed",
            "error": "yt-dlp not installed. Run: pip install yt-dlp",
            "downloaded_files": [],
        }

    output_dir = state.get("output_dir")
    url = state.get("url", "")
    fmt = state.get("format", "mp3")

    if not output_dir or not os.path.isdir(output_dir):
        print("[Converter Workflow] Step: download_failed (no output dir)")
        return {
            **state,
            "step": "download_failed",
            "error": "Output directory not set.",
            "downloaded_files": [],
        }

    out_tmpl = os.path.join(output_dir, "%(playlist_index)s - %(title)s.%(ext)s")
    # Single video: avoid "1 - " prefix by using different template when not playlist
    out_tmpl_single = os.path.join(output_dir, "%(title)s.%(ext)s")

    if fmt == "mp3":
        ydl_opts = {
            "outtmpl": out_tmpl,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }
    else:
        ydl_opts = {
            "outtmpl": out_tmpl,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }

    print("[Converter Workflow] Step: downloading (format=" + fmt + ")")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        err = str(e)
        print("[Converter Workflow] Step: download_failed - " + err[:200])
        return {
            **state,
            "step": "download_failed",
            "error": "Download failed: " + err[:300],
            "downloaded_files": [],
        }

    # Collect downloaded files (after postprocessors, so look for .mp3 or .mp4)
    exts = (".mp3", ".mp4", ".m4a", ".webm")
    downloaded = []
    for f in sorted(Path(output_dir).iterdir()):
        if f.is_file() and f.suffix.lower() in exts:
            downloaded.append(str(f))

    if not downloaded:
        print("[Converter Workflow] Step: download_failed (no files produced)")
        return {
            **state,
            "step": "download_failed",
            "error": "No media files produced. Check URL and format.",
            "downloaded_files": [],
        }

    print("[Converter Workflow] Downloaded " + str(len(downloaded)) + " file(s)")
    return {
        **state,
        "downloaded_files": downloaded,
        "step": "downloaded",
        "error": None,
    }
