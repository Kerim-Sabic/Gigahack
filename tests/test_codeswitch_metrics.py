import pytest

from scripts.codeswitch_metrics import score_codeswitch


@pytest.mark.parametrize('reference,hypothesis,languages,minority', [
    ('Vă rog luați acest medicament dimineața după masă хорошо azi',
     'Vă rog luați acest medicament dimineața după masă bine azi', ['ro']*8+['ru','ro'], 'ru'),
    ('Пожалуйста принимайте это лекарство утром после еды каждый день mâine',
     'Пожалуйста принимайте это лекарство утром после еды каждый день завтра', ['ru']*9+['ro'], 'ro'),
])
def test_low_overall_wer_cannot_hide_missing_one_word_switch(reference, hypothesis, languages, minority):
    result = score_codeswitch(reference,hypothesis,languages,minority_language=minority)
    assert result['wer'] == .1
    assert result['minority_word_recall'] == 0
    assert result['minority_word_precision'] is None
    assert result['missing_hypothesis_labels'].startswith('NOT MEASURED')


def test_extra_minority_word_reduces_precision_and_breaks_boundary():
    result = score_codeswitch('luați хорошо azi','luați хорошо спасибо azi', ['ro','ru','ro'],
                              minority_language='ru',hypothesis_languages=['ro','ru','ru','ro'])
    assert result['minority_word_recall'] == 1
    assert result['minority_word_precision'] == .5
    assert result['switch_boundary_recall'] == .5
    assert result['per_language']['ru']['wer'] == 1


def test_native_script_diacritics_not_erased_by_normalization():
    result = score_codeswitch('mâine хорошо','maine khorosho',['ro','ru'],minority_language='ru')
    assert result['wer'] == 1
    assert result['minority_word_recall'] == 0


def test_missing_reference_annotations_rejected():
    with pytest.raises(ValueError,match='reference_token_languages_required'):
        score_codeswitch('după masă','după masă',['ro'],minority_language='ru')
