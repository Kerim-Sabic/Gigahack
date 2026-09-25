import hashlib
import json
import os
import subprocess
import wave
from pathlib import Path

from . import config


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".partial")
    with temp.open("wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def decode(path, target):
    """Only filesystem paths constructed by the server reach FFmpeg."""
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        timeout=30,
        check=True,
    )
    info = json.loads(probe.stdout)
    streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if not streams:
        raise ValueError("no_audio_stream")
    duration = float(info.get("format", {}).get("duration", 0))
    if duration <= 0 or duration > config.MAX_SECONDS:
        raise ValueError("invalid_audio_duration")
    target = Path(target)
    temporary = target.with_name(target.stem + ".partial.wav")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-t",
            str(config.MAX_SECONDS + 1),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(temporary),
        ],
        capture_output=True,
        timeout=300,
        check=True,
    )
    with wave.open(str(temporary)) as w:
        samples, rate = w.getnframes(), w.getframerate()
    if samples / rate > config.MAX_SECONDS:
        temporary.unlink(missing_ok=True)
        raise ValueError("decoded_duration_exceeded")
    with temporary.open("r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    return dict(
        sample_rate=rate,
        samples=samples,
        channels=1,
        original=json.dumps(
            {
                "rate": streams[0].get("sample_rate"),
                "channels": streams[0].get("channels"),
                "duration": duration,
            }
        ),
    )


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()
