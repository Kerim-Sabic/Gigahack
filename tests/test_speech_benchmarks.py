import hashlib
import json

import pytest

from scripts.audio_metrics import character_score
from scripts.benchmark_speech import validate_cases
from services.speech.baselines import native_words


def test_case_integrity_and_reference_provenance(tmp_path):
    audio=tmp_path/'source.wav'
    audio.write_bytes(b'identity test; decoding is a separate integration check')
    manifest=tmp_path/'cases.json'
    case={'id':'clip','audio':'source.wav','sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),
          'reference_text':'după masă','provenance':{'review_status':'synthetic unit fixture'}}
    manifest.write_text(json.dumps([case]))
    assert validate_cases(manifest)[0]['audio'] == str(audio.resolve())
    audio.write_bytes(b'changed')
    with pytest.raises(ValueError,match='source_clip_missing_or_changed'):
        validate_cases(manifest)


def test_invalid_native_word_times_are_unavailable_not_invented():
    assert native_words([('word',0,0)],16000,32000,'test') is None
    assert native_words([('word',0,2)],16000,32000,'test') is None
    word=native_words([('word',.1,.2)],16000,32000,'test')[0]
    assert (word.start_sample,word.end_sample) == (17600,19200)


def test_cer_preserves_critical_decimal_separator_and_accents():
    assert character_score('0,5','0.5')['character_errors'] == 1
    assert character_score('Ș','S')['cer'] == 1
    assert character_score('а','a')['cer'] == 1  # Cyrillic versus Latin
    assert character_score('abc','ABC')['cer'] == 0
