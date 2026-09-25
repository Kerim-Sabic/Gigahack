import pytest

from services.api.minutes import render


@pytest.mark.parametrize(
    "language, heading, owner",
    [
        ("en", "Meeting minutes", "Owner"),
        ("ro", "Proces-verbal", "Responsabil"),
        ("ru", "Протокол совещания", "Ответственный"),
    ],
)
def test_minutes_localize_template_but_preserve_and_escape_accepted_text(language, heading, owner):
    source = "Elena <script>unsafe()</script> ședință в среду"
    data = {
        "meeting": {
            "title": "Synthetic",
            "date": "2026-09-25",
            "timezone": "Europe/Chisinau",
            "classification": "Administrative",
            "revision": 1,
            "language": language,
        },
        "participants": ["Elena"],
        "unresolved": [],
        "items": [
            {
                "text": source,
                "owner": None,
                "due": None,
                "status": "confirmed",
                "condition": None,
                "history": [],
            }
        ],
    }
    output = render(data)
    assert heading in output and f"<th>{owner}</th>" in output
    assert "<script>" not in output and "&lt;script&gt;" in output
    assert "ședință в среду" in output
