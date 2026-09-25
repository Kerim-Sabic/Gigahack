from services.worker.audio_checks import speech_gaps


def test_overlapping_speakers_and_transcript_spans_do_not_duplicate_missing_speech():
    turns = [{"start": 0, "end": 5}, {"start": 3, "end": 9}, {"start": 10, "end": 12}]
    segments = [{"start": 16000, "end": 3*16000, "text": "Russian and Romanian"},
                {"start": 2*16000, "end": 4*16000, "text": "overlap"},
                {"start": 6*16000, "end": 8*16000, "text": "words"},
                {"start": 10*16000, "end": 12*16000, "text": "   "}]
    assert list(speech_gaps(turns, segments, 12*16000)) == [
        {"start": 0, "end": 16000}, {"start": 4*16000, "end": 6*16000},
        {"start": 8*16000, "end": 9*16000}, {"start": 10*16000, "end": 12*16000}]


def test_source_bounds_short_timing_edges_and_silence():
    assert list(speech_gaps([], [], 16000)) == []
    assert list(speech_gaps([{"start": -1, "end": 20}], [], 16000)) == [{"start": 0, "end": 16000}]
    assert list(speech_gaps([{"start": 0, "end": 1}], [{"start": 7000, "end": 16000, "text": "words"}], 16000)) == []
