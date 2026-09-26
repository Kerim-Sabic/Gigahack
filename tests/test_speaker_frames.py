from services.speech.nemotron import SpeakerTurns


def test_speakers_persist_across_blocks_and_overlap_is_retained():
    turns=SpeakerTurns(650,speakers=2)
    turns.feed([[True,False],[True,True]])
    turns.feed([[True,True],[False,True],[False,True]])
    assert turns.finish() == [
        {'start_sample':0,'end_sample':480,'cluster':'SPEAKER_00'},
        {'start_sample':160,'end_sample':650,'cluster':'SPEAKER_01'},
    ]


def test_padding_cannot_create_speech_beyond_source():
    turns=SpeakerTurns(100,speakers=1)
    turns.feed([[True],[True],[True]])
    assert turns.finish() == [{'start_sample':0,'end_sample':100,'cluster':'SPEAKER_00'}]
