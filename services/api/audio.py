import hashlib
import math
import time
import threading
from collections import deque

import psutil
import json
import os
import subprocess
import wave
from pathlib import Path

from . import config
from .pcm import Reader
from .storage import require_space


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".partial")
    with temp.open("wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def run_decoder(command, target):
    """Monitor actual output/CPU activity, bound stderr memory, and always reap the child."""
    tail = deque(maxlen=2)
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def read_errors():
        while block := process.stderr.read(4096):
            tail.append(block)

    reader = threading.Thread(target=read_errors, daemon=True)
    reader.start()
    try:
        observed = psutil.Process(process.pid)
    except psutil.NoSuchProcess:
        observed = None
    last_activity, previous_size, previous_cpu = time.monotonic(), 0, 0.0
    try:
        while process.poll() is None:
            require_space(target.parent)
            size = target.stat().st_size if target.exists() else 0
            try:
                if observed is None:
                    raise psutil.NoSuchProcess(process.pid)
                cpu_times = observed.cpu_times()
                cpu = cpu_times.user + cpu_times.system
            except psutil.NoSuchProcess:
                cpu = previous_cpu
            if size > previous_size or cpu > previous_cpu + 0.01:
                last_activity = time.monotonic()
            previous_size, previous_cpu = size, cpu
            if time.monotonic() - last_activity > config.DECODE_IDLE_SECONDS:
                raise TimeoutError("audio_decode_stalled")
            time.sleep(0.1)
        reader.join(timeout=5)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, command, stderr=b"".join(tail))
        require_space(target.parent)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        reader.join(timeout=5)
        process.stderr.close()


def decode(path, target):
    """Only filesystem paths constructed by the server reach FFmpeg."""
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_entries",
            "format=duration:stream=codec_type,sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
        check=True,
    )
    info = json.loads(probe.stdout)
    streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if not streams:
        raise ValueError("no_audio_stream")
    raw_duration = info.get("format", {}).get("duration")
    duration = float(raw_duration) if raw_duration not in (None, "N/A") else None
    if duration is not None and (not math.isfinite(duration) or duration <= 0 or
                                 (config.MAX_SECONDS and duration > config.MAX_SECONDS)):
        raise ValueError("invalid_audio_duration")
    require_space(Path(target).parent, math.ceil(duration * 32000) if duration else 0)
    target = Path(target)
    temporary = target.with_name(target.stem + ".partial.wav")
    run_decoder(
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
            *(["-t", str(config.MAX_SECONDS + 1)] if config.MAX_SECONDS else []),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-rf64",
            "auto",
            str(temporary),
        ],
        temporary,
    )
    with Reader(temporary) as w:
        samples, rate = w.getnframes(), w.getframerate()
    if samples <= 0 or (config.MAX_SECONDS and samples / rate > config.MAX_SECONDS):
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


def canonical_clip(source, target, start, end):
    """Copy exact source samples with bounded buffers, without repeated decoding."""
    target = Path(target)
    temporary = target.with_suffix(".partial.wav")
    with Reader(source) as reader:
        if (reader.getframerate(), reader.getnchannels(), reader.getsampwidth()) != (16000, 1, 2):
            raise ValueError("clip_requires_canonical_audio")
        if not 0 <= start < end <= reader.getnframes():
            raise ValueError("clip_outside_source")
        reader.setpos(start)
        with wave.open(str(temporary), "wb") as writer:
            writer.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            remaining = end - start
            while remaining:
                count = min(remaining, 512 * 1024)
                data = reader.readframes(count)
                if len(data) != count * 2:
                    raise ValueError("truncated_canonical_audio")
                writer.writeframesraw(data)
                remaining -= count
    with temporary.open("r+b") as stream:
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def clip_bytes(path, start, end, first, last):
    """Stream a byte range of a virtual small WAV without creating another disk copy."""
    from .pcm import header

    prefix = header(end - start)
    if first < len(prefix):
        yield prefix[first:min(last + 1, len(prefix))]
    data_first = max(0, first - len(prefix))
    remaining = last + 1 - max(first, len(prefix))
    if remaining > 0:
        with Reader(path) as source:
            source.stream.seek(source.offset + start * 2 + data_first)
            while remaining:
                block = source.stream.read(min(remaining, 65536))
                if not block:
                    raise ValueError("truncated_canonical_audio")
                yield block
                remaining -= len(block)
