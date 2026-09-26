"""Minority-word metrics from explicit token annotations, never guessed from script.

Use separately reviewed gold and source-aligned clips. Synthetic fixtures validate
the scorer only. Hypothesis language labels must come from an identified annotator
or model; omission leaves precision/boundary classification NOT MEASURED.
"""

from collections import Counter

from scripts.audio_metrics import score


def score_codeswitch(reference, hypothesis, reference_languages, *, minority_language,
                     hypothesis_languages=None, critical_spans=()):
    base = score(reference, hypothesis, critical_spans)
    ref, hyp = base['reference_tokens'], base['hypothesis_tokens']
    allowed = {'ro', 'ru', 'en', 'other', 'unknown'}
    if len(reference_languages) != len(ref) or any(x not in allowed for x in reference_languages):
        raise ValueError('reference_token_languages_required')
    if minority_language not in {'ro', 'ru', 'en'}:
        raise ValueError('explicit_minority_language_required')
    if hypothesis_languages is not None and (
        len(hypothesis_languages) != len(hyp) or any(x not in allowed for x in hypothesis_languages)
    ):
        raise ValueError('invalid_hypothesis_token_languages')
    counts = Counter(reference_languages)
    per_language = {language: {'reference_words': count, 'correct': 0,
                              'substitutions': 0, 'deletions': 0, 'insertions': 0}
                    for language, count in counts.items()}
    matched = {}
    for edit in base['alignment']:
        i, j, op = edit['reference'], edit['hypothesis'], edit['op']
        if op == 'insert':
            if hypothesis_languages is not None:
                language = hypothesis_languages[j]
                row = per_language.setdefault(language, {'reference_words': 0, 'correct': 0,
                                                          'substitutions': 0, 'deletions': 0, 'insertions': 0})
                row['insertions'] += 1
            continue
        language = reference_languages[i]
        per_language[language][{'equal': 'correct', 'substitute': 'substitutions', 'delete': 'deletions'}[op]] += 1
        if op == 'equal':
            matched[i] = j
    for row in per_language.values():
        row['wer'] = ((row['substitutions'] + row['deletions'] + row['insertions']) / row['reference_words']
                      if row['reference_words'] and hypothesis_languages is not None else None)
    minority_ref = [i for i, language in enumerate(reference_languages) if language == minority_language]
    correct_words = sum(i in matched for i in minority_ref)
    precision = boundary_recall = None
    boundaries = [i for i in range(1, len(ref))
                  if reference_languages[i] != reference_languages[i-1]
                  and reference_languages[i] not in {'unknown', 'other'}
                  and reference_languages[i-1] not in {'unknown', 'other'}]
    if hypothesis_languages is not None:
        predicted = hypothesis_languages.count(minority_language)
        correct_labeled = sum(i in matched and hypothesis_languages[matched[i]] == minority_language for i in minority_ref)
        precision = correct_labeled / predicted if predicted else None
        correct_boundaries = sum(
            i-1 in matched and i in matched and matched[i] == matched[i-1] + 1
            and hypothesis_languages[matched[i-1]] == reference_languages[i-1]
            and hypothesis_languages[matched[i]] == reference_languages[i]
            for i in boundaries
        )
        boundary_recall = correct_boundaries / len(boundaries) if boundaries else None
    return {
        **base,
        'per_language': per_language,
        'minority_language': minority_language,
        'minority_reference_words': len(minority_ref),
        'minority_words_preserved': correct_words,
        'minority_word_recall': correct_words / len(minority_ref) if minority_ref else None,
        'minority_word_precision': precision,
        'language_switch_boundaries': len(boundaries),
        'switch_boundary_recall': boundary_recall,
        'boundary_definition': 'Both adjacent reference words preserved adjacently, with correct explicit hypothesis language labels; not acoustic timing accuracy',
        'missing_hypothesis_labels': 'NOT MEASURED: per-language WER, minority precision and boundary classification' if hypothesis_languages is None else None,
        'native_script_and_diacritics': 'Exact normalized token matching; transliteration and accent removal count as errors',
    }
