import os
import struct
import subprocess
import wave

import pytest

from services.api.audio import canonical_clip
from services.api.pcm import Reader, header


def test_rf64_matches_ffmpeg_and_exact_source_clip(tmp_path):
    source = tmp_path / "rf64.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000", "-t", "1", "-c:a", "pcm_s16le", "-rf64", "always", str(source)], check=True)
    with Reader(source) as reader:
        assert reader.getnframes() == 16000
        expected = reader.readframes(16000)[200:2000]
    target = tmp_path / "clip.wav"
    canonical_clip(source, target, 100, 1000)
    with wave.open(str(target)) as reader:
        assert reader.readframes(900) == expected


@pytest.mark.parametrize("fault", ["truncated", "size", "count", "format"])
def test_rf64_rejects_invalid_sizes_and_format(tmp_path, fault):
    data = bytearray(header(100, force_rf64=True) + b"\0\0" * 100)
    if fault == "truncated":
        data = data[:-2]
    elif fault == "size":
        struct.pack_into("<Q", data, 28, 300)
    elif fault == "count":
        struct.pack_into("<Q", data, 36, 101)
    else:
        struct.pack_into("<H", data, 56, 3)  # Only integer PCM16 is canonical.
    source = tmp_path / "invalid.wav"
    source.write_bytes(data)
    with pytest.raises(ValueError):
        Reader(source)


@pytest.mark.skipif(os.name == "nt", reason="Large sparse-file check uses the Linux qualification filesystem")
def test_exact_reads_and_clips_beyond_four_gib_without_loading_the_file(tmp_path):
    source = tmp_path / "large.wav"
    frames = 2**31 + 123
    start = frames - 4
    with source.open("wb") as stream:
        stream.write(header(frames))
        stream.seek(80 + start * 2)
        stream.write(b"\1\0\2\0\3\0\4\0")
    with Reader(source) as reader:
        assert reader.getnframes() == frames
        reader.setpos(start)
        assert reader.readframes(4) == b"\1\0\2\0\3\0\4\0"
    target = tmp_path / "tail.wav"
    canonical_clip(source, target, start, frames)
    with wave.open(str(target)) as reader:
        assert reader.readframes(4) == b"\1\0\2\0\3\0\4\0"
