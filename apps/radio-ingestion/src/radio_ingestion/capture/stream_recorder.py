"""Stream recorder using ffmpeg for audio capture"""

import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class StreamRecorder:
    """Record audio streams using ffmpeg"""

    def __init__(
        self, output_dir: str, sample_rate: int = 22050, channels: int = 1, format: str = "wav"
    ):
        """
        Initialize stream recorder.

        Args:
            output_dir: Directory to save recorded files
            sample_rate: Target sample rate (default: 22050, matches audio-lane)
            channels: Number of channels (default: 1 for mono)
            format: Output format (default: wav)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = format

        # Verify ffmpeg is available
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if ffmpeg is available"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError("ffmpeg is not working properly")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg is not installed. Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg check timed out")

    def record_stream(
        self,
        stream_url: str,
        duration: int,
        output_filename: Optional[str] = None,
        reconnect: bool = True,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Record audio stream for specified duration.

        Args:
            stream_url: URL of the audio stream
            duration: Duration in seconds
            output_filename: Optional output filename (auto-generated if not provided)
            reconnect: Whether to attempt reconnection on failure
            max_retries: Maximum number of reconnection attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Dictionary with:
                - path: Path to recorded file
                - duration: Actual duration recorded
                - file_size: File size in bytes
                - success: Whether recording succeeded
                - error: Error message if failed
                - error_code: ffmpeg return code
                - error_kind: Classified failure kind
                - error_detail: Short error summary
        """
        if output_filename is None:
            # Generate filename: stream_YYYYMMDD_HHMMSS.wav
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_filename = f"stream_{timestamp}.{self.format}"

        output_path = self.output_dir / output_filename

        # Build ffmpeg command
        # Normalize to mono 22.05kHz WAV (matches audio-lane format)
        cmd = [
            "ffmpeg",
            "-i",
            stream_url,  # Input stream
            "-ar",
            str(self.sample_rate),  # Sample rate
            "-ac",
            str(self.channels),  # Channels (mono)
            "-f",
            self.format,  # Output format
            "-t",
            str(duration),  # Duration
            "-y",  # Overwrite output file
            str(output_path),
        ]

        attempt = 0
        last_error = None
        error_code = None
        error_kind = None
        error_detail = None

        while attempt <= max_retries:
            try:
                logger.info(
                    "Starting stream recording",
                    stream_url=stream_url,
                    duration=duration,
                    output_path=str(output_path),
                    attempt=attempt + 1,
                )

                # Run ffmpeg with timeout (add 10% buffer)
                timeout = duration + 10
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=(
                        os.setsid if hasattr(os, "setsid") else None
                    ),  # Create new process group
                )

                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    returncode = process.returncode

                    if returncode == 0 and output_path.exists():
                        # Verify file exists and has content
                        file_size = output_path.stat().st_size

                        if file_size > 0:
                            logger.info(
                                "Stream recording successful",
                                output_path=str(output_path),
                                file_size=file_size,
                                duration=duration,
                            )

                            return {
                                "path": str(output_path),
                                "duration": duration,
                                "file_size": file_size,
                                "success": True,
                                "error": None,
                            }
                        else:
                            last_error = "Output file is empty"
                    else:
                        # ffmpeg failed
                        stderr_text = stderr.decode("utf-8", errors="ignore")
                        error_code = returncode
                        error_kind, error_detail = self._classify_error(stderr_text)
                        last_error = f"ffmpeg returned {returncode}: {stderr_text[:500]}"

                except subprocess.TimeoutExpired:
                    # Kill process group on timeout
                    try:
                        if hasattr(os, "setsid"):
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        else:
                            process.terminate()
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()

                    error_kind = "timeout"
                    error_detail = f"timeout {timeout}s"
                    last_error = f"Recording timed out after {timeout} seconds"

            except Exception as e:
                error_kind = "exception"
                error_detail = str(e)
                last_error = f"Recording failed: {str(e)}"

            # Retry logic
            if reconnect and attempt < max_retries:
                attempt += 1
                logger.warning(
                    "Recording failed, retrying",
                    attempt=attempt,
                    max_retries=max_retries,
                    error=last_error,
                    retry_delay=retry_delay,
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                break

        # All retries exhausted
        logger.error(
            "Stream recording failed after retries",
            stream_url=stream_url,
            output_path=str(output_path),
            error=last_error,
            attempts=attempt + 1,
        )

        # Clean up partial file if it exists
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass

        return {
            "path": str(output_path) if output_path.exists() else None,
            "duration": 0,
            "file_size": 0,
            "success": False,
            "error": last_error,
            "error_code": error_code,
            "error_kind": error_kind,
            "error_detail": error_detail,
        }

    def _classify_error(self, stderr_text: str) -> tuple[str, str]:
        if not stderr_text:
            return "unknown", "no stderr"
        lowered = stderr_text.lower()
        if "404" in lowered or "not found" in lowered:
            return "not_found", "404 or not found"
        if "403" in lowered or "forbidden" in lowered:
            return "forbidden", "403 forbidden"
        if "401" in lowered or "unauthorized" in lowered:
            return "unauthorized", "401 unauthorized"
        if "connection refused" in lowered:
            return "connection_refused", "connection refused"
        if "timed out" in lowered or "timeout" in lowered:
            return "timeout", "connection timeout"
        if "could not resolve" in lowered or "name or service not known" in lowered:
            return "dns", "dns failure"
        if "tls" in lowered or "ssl" in lowered:
            return "tls", "tls/ssl error"
        if "http error" in lowered:
            match = re.search(r"http error (\d+)", lowered)
            if match:
                return "http_error", f"http {match.group(1)}"
        return "ffmpeg_error", stderr_text[:120].strip()

    def get_audio_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get audio file metadata using ffprobe.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary with audio info (bitrate, codec, sample_rate, duration) or None
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=bit_rate,duration,format_name",
                "-show_entries",
                "stream=sample_rate,codec_name,channels",
                "-of",
                "json",
                file_path,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=10, check=True)

            import json

            data = json.loads(result.stdout.decode("utf-8"))

            info = {}
            if "format" in data:
                format_data = data["format"]
                info["bitrate"] = (
                    int(format_data.get("bit_rate", 0)) // 1000
                    if format_data.get("bit_rate")
                    else None
                )
                info["duration"] = float(format_data.get("duration", 0))
                info["codec"] = (
                    format_data.get("format_name", "").split(",")[0]
                    if format_data.get("format_name")
                    else None
                )

            if "streams" in data and len(data["streams"]) > 0:
                stream_data = data["streams"][0]
                info["sample_rate"] = int(stream_data.get("sample_rate", 0))
                info["channels"] = int(stream_data.get("channels", 0))

            return info if info else None

        except Exception as e:
            logger.warning("Failed to get audio info", file_path=file_path, error=str(e))
            return None
