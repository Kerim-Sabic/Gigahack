"""Conservative calendar parsing; model dates are never authority."""

import re
from datetime import date, timedelta

MONTHS = {
    "january": 1,
    "ianuarie": 1,
    "января": 1,
    "february": 2,
    "februarie": 2,
    "февраля": 2,
    "march": 3,
    "martie": 3,
    "марта": 3,
    "april": 4,
    "aprilie": 4,
    "апреля": 4,
    "may": 5,
    "mai": 5,
    "мая": 5,
    "june": 6,
    "iunie": 6,
    "июня": 6,
    "july": 7,
    "iulie": 7,
    "июля": 7,
    "august": 8,
    "августа": 8,
    "september": 9,
    "septembrie": 9,
    "сентября": 9,
    "october": 10,
    "octombrie": 10,
    "октября": 10,
    "november": 11,
    "noiembrie": 11,
    "ноября": 11,
    "december": 12,
    "decembrie": 12,
    "декабря": 12,
}


def resolve(raw, meeting_date):
    if not raw:
        return None
    raw = raw.strip().lower()
    try:
        base = date.fromisoformat(meeting_date) if meeting_date else None
    except ValueError:
        base = None
    if raw in ("tomorrow", "mâine", "завтра"):
        return (base + timedelta(days=1)).isoformat() if base else None
    if raw in ("today", "astăzi", "сегодня"):
        return base.isoformat() if base else None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            return date.fromisoformat(raw).isoformat()
        except ValueError:
            return None
    for month, number in MONTHS.items():
        match = re.search(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+" + month, raw)
        if not match:
            match = re.search(month + r"\s+(\d{1,2})(?:st|nd|rd|th)?", raw)
        if match:
            year = re.search(r"\b(20\d{2})\b", raw)
            if not year and not base:
                return None
            try:
                return date(int(year[1]) if year else base.year, number, int(match[1])).isoformat()
            except ValueError:
                return None
    return None
