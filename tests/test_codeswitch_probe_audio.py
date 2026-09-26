import numpy as np
import pytest

from scripts.prepare_codeswitch_probe import pcm16_bytes


def test_normalized_float_audio_keeps_audible_pcm_amplitude():
    decoded = np.frombuffer(pcm16_bytes(np.array([0, .5, -.5, 1, -1], dtype=np.float32)), dtype='<i2')
    assert decoded.tolist() == [0, 16384, -16384, 32767, -32767]


def test_nonfinite_audio_is_rejected_instead_of_becoming_silence():
    with pytest.raises(ValueError):
        pcm16_bytes(np.array([float('nan')]))
