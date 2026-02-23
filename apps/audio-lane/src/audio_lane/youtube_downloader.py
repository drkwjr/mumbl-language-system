"""
YouTube audio downloader using yt-dlp.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


def _require_yt_dlp():
    try:
        import yt_dlp
    except ImportError as exc:
        raise ImportError(
            "yt-dlp is required for YouTube downloads. Install with: pip install yt-dlp"
        ) from exc
    return yt_dlp


def download_audio(
    url: str, output_dir: str = "data/audio/raw", language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Download audio from YouTube URL.

    Args:
        url: YouTube URL
        output_dir: Directory to save audio files
        language: Optional language code for metadata

    Returns:
        Dict with keys: audio_path, duration, metadata
    """
    os.makedirs(output_dir, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "no_warnings": False,
    }

    metadata = {}
    duration = None
    audio_path = None

    try:
        yt_dlp = _require_yt_dlp()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to get metadata
            info = ydl.extract_info(url, download=False)
            video_id = info.get("id")
            duration = info.get("duration", 0)
            title = info.get("title", "")
            uploader = info.get("uploader", "")

            metadata = {
                "video_id": video_id,
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "url": url,
                "language": language,
            }

            # Download
            ydl.download([url])

            # Find the downloaded file
            downloaded_files = list(Path(output_dir).glob(f"{video_id}.*"))
            wav_files = [f for f in downloaded_files if f.suffix == ".wav"]

            if wav_files:
                audio_path = str(wav_files[0])
            else:
                # Fallback: look for any audio file
                audio_files = [f for f in downloaded_files if f.suffix in [".wav", ".mp3", ".m4a"]]
                if audio_files:
                    audio_path = str(audio_files[0])
                    # Convert to WAV if needed
                    # (Could add conversion here if needed)

    except Exception as e:
        raise RuntimeError(f"Failed to download audio from {url}: {str(e)}")

    if not audio_path or not os.path.exists(audio_path):
        raise RuntimeError(f"Downloaded audio file not found for {url}")

    return {
        "audio_path": audio_path,
        "duration": duration,
        "metadata": metadata,
    }
