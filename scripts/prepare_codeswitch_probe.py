"""Construct labelled splicing probes, never a natural code-switch accuracy corpus."""

import argparse
import hashlib
import json
import wave
from pathlib import Path

from scripts.audio_metrics import tokens


def pcm16_bytes(samples):
    import numpy as np

    if samples.ndim != 1 or not len(samples) or not np.isfinite(samples).all():
        raise ValueError('invalid_probe_audio')
    # libsndfile's float-file -> integer read does not scale normalized floats.
    # Decode to float first, then explicitly scale; otherwise speech becomes zeros.
    return np.rint(np.clip(samples, -1, 1)*32767).astype('<i2').tobytes()


def construct(cases_path, timing_report, destination):
    import soundfile

    cases = {case['id']: case for case in json.loads(cases_path.read_text(encoding='utf-8'))}
    observed = {case['id']: case for case in json.loads(timing_report.read_text(encoding='utf-8'))['cases']}
    destination.mkdir(parents=True, exist_ok=True)
    prepared = {}
    for name in ('ro_ro-1576', 'ru_ru-1614'):
        case, result = cases[name], observed[name]
        path = Path(case['audio'])
        path = path if path.is_absolute() else cases_path.parent/path
        if hashlib.sha256(path.read_bytes()).hexdigest() != case['sha256']:
            raise ValueError('probe_source_changed')
        words = [word for segment in result['observed']['raw']['segments'] for word in segment['words']]
        if tokens(case['reference_text']) != tokens(' '.join(word['word'] for word in words)):
            raise ValueError('timing_transcript_does_not_match_publisher_reference')
        if any(len(tokens(word['word'])) != 1 for word in words):
            raise ValueError('probe_requires_one_token_per_timed_word')
        samples, rate = soundfile.read(path, dtype='float32')
        if rate != 16000 or samples.ndim != 1:
            raise ValueError('probe_requires_mono_16khz_source')
        pcm = pcm16_bytes(samples)
        if max(abs(int.from_bytes(pcm[i:i+2], 'little', signed=True)) for i in range(0, len(pcm), 2)) < 100:
            raise ValueError('probe_speech_source_is_effectively_silent')
        prepared[name] = (pcm, words)
    output = []
    # Selection declared before VibeVoice probe inference; timings are model estimates.
    for main, foreign, lo, hi in [('ro_ro-1576', 'ru_ru-1614', 6, 9), ('ru_ru-1614', 'ro_ro-1576', 14, 17)]:
        pcm, words = prepared[main]
        other, other_words = prepared[foreign]
        insertion = 6
        cut = round(words[insertion-1]['end']*16000)
        start = round(other_words[lo]['start']*16000)
        end = round(other_words[hi-1]['end']*16000)
        if not 0 < cut*2 < len(pcm) or not 0 <= start < end <= len(other)//2:
            raise ValueError('invalid_probe_cut')
        silence = b'\0'*(800*2)  # 50 ms at each join; source voices change.
        combined = pcm[:cut*2]+silence+other[start*2:end*2]+silence+pcm[cut*2:]
        target = destination/f'{main[:2]}-three-{foreign[:2]}-words.wav'
        with wave.open(str(target), 'wb') as stream:
            stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            stream.writeframes(combined)
        text = ' '.join(word['word'].strip() for word in [*words[:insertion], *other_words[lo:hi], *words[insertion:]])
        languages = [main[:2]]*insertion+[foreign[:2]]*(hi-lo)+[main[:2]]*(len(words)-insertion)
        assert len(tokens(text)) == len(languages)
        output.append({'id': target.stem, 'audio': str(target.resolve()),
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'reference_text': text,
            'reference_languages': languages, 'minority_language': foreign[:2],
            'provenance': {'review_status': 'CONSTRUCTED PROBE; publisher words, model-estimated cuts, no human boundary review',
                'dataset': 'google/fleurs', 'revision': cases[main]['provenance']['revision'], 'license': 'CC-BY-4.0',
                'main_source': main, 'main_sha256': cases[main]['sha256'], 'main_insert_sample': cut,
                'foreign_source': foreign, 'foreign_sha256': cases[foreign]['sha256'], 'foreign_samples': [start, end],
                'timing_report_sha256': hashlib.sha256(timing_report.read_bytes()).hexdigest(),
                'audio_conversion': 'libsndfile float32 decode, explicit normalized float to PCM16 scaling; 50ms zero padding at each join',
                'scope': 'Artificial joins, different voices and unnatural sentences; not medical/Moldovan/natural code-switch accuracy'}})
    manifest = destination/'cases.json'
    manifest.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'manifest': str(manifest), 'cases': len(output), 'scope': 'constructed probes only'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--timing-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    construct(args.cases, args.timing_report, args.output)
