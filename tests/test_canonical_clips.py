import struct
import wave

import pytest

from services.api.audio import canonical_clip


def test_clip_preserves_exact_samples_across_buffer_boundary(tmp_path):
    source, target = tmp_path / "source.wav", tmp_path / "clip.wav"
    samples = b"".join(struct.pack("<h", i % 32768) for i in range(600000))
    with wave.open(str(source), "wb") as writer:
        writer.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        writer.writeframes(samples)
    canonical_clip(source, target, 117, 599987)
    with wave.open(str(target), "rb") as reader:
        assert reader.getnframes() == 599987 - 117
        assert reader.readframes(reader.getnframes()) == samples[117 * 2:599987 * 2]
    before = target.read_bytes()
    for start, end in ((-1, 1), (5, 5), (0, 600001)):
        with pytest.raises(ValueError, match="clip_outside_source"):
            canonical_clip(source, target, start, end)
        assert target.read_bytes() == before


def test_truncated_source_never_publishes_clip(tmp_path):
    source, target = tmp_path / "source.wav", tmp_path / "clip.wav"
    with wave.open(str(source), "wb") as writer:
        writer.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        writer.writeframes(b"\0\0" * 100)
    source.write_bytes(source.read_bytes()[:-30])
    with pytest.raises(ValueError, match="truncated_canonical_audio"):
        canonical_clip(source, target, 0, 100)
    assert not target.exists()
