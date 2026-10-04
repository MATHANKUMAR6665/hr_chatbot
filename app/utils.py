"""
utils.py - Small helper functions: date parsing, number parsing, yes/no detection.

WHAT : Turns text like "October 8" or "tomorrow" into a real date, "two" into 2, etc.
WHY  : Keeps entity_extractor.py and dialogue_manager.py short and readable.
USED BY : entity_extractor.py, dialogue_manager.py, responses.py
CONCEPT : Entity normalization (#6), error handling for invalid dates (#17).
"""
import re
from datetime import date, timedelta

MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
          "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
          "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
          "sept": 9, "oct": 10, "nov": 11, "dec": 12}
WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4,
            "saturday": 5, "sunday": 6}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
WEEKDAY_RE = "|".join(WEEKDAYS)
NUM_WORD_RE = "|".join(NUMBER_WORDS)

# One regex with several alternatives: "8 October", "October 8", 2026-10-08, 08/10/2026, tomorrow, Monday
_DATE_RE = re.compile(
    rf"(?:\b(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?(?P<m1>{MONTH_RE})\b(?:,?\s+(?P<y1>\d{{4}}))?)"
    rf"|(?:\b(?P<m2>{MONTH_RE})\.?\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(?P<y2>\d{{4}}))?)"
    rf"|(?:\b(?P<y3>\d{{4}})-(?P<m3>\d{{1,2}})-(?P<d3>\d{{1,2}})\b)"
    rf"|(?:\b(?P<d4>\d{{1,2}})/(?P<m4>\d{{1,2}})/(?P<y4>\d{{4}})\b)"
    rf"|(?:\b(?P<rel>day after tomorrow|tomorrow|today)\b)"
    rf"|(?:\b(?:(?:next|this|coming)\s+)?(?P<wd>{WEEKDAY_RE})\b)",
    re.IGNORECASE)


def _build_date(m, today):
    """Convert one regex match into a date. Raises ValueError for impossible dates (e.g. Oct 45)."""
    g = m.groupdict()
    if g["rel"]:
        offset = {"today": 0, "tomorrow": 1, "day after tomorrow": 2}[g["rel"].lower()]
        return today + timedelta(days=offset)
    if g["wd"]:
        ahead = (WEEKDAYS[g["wd"].lower()] - today.weekday()) % 7
        return today + timedelta(days=ahead or 7)
    if g["y3"]:
        return date(int(g["y3"]), int(g["m3"]), int(g["d3"]))
    if g["y4"]:
        return date(int(g["y4"]), int(g["m4"]), int(g["d4"]))
    if g["m1"]:
        day, month, year = int(g["d1"]), MONTHS[g["m1"].lower()], g["y1"]
    else:
        day, month, year = int(g["d2"]), MONTHS[g["m2"].lower()], g["y2"]
    if year:
        return date(int(year), month, day)
    result = date(today.year, month, day)       # may raise ValueError
    return result if result >= today else date(today.year + 1, month, day)


def find_dates(text, today=None):
    """Return [{'text': 'October 8', 'date': date(...) or None}] in order of appearance."""
    today = today or date.today()
    found = []
    for m in _DATE_RE.finditer(text):
        try:
            found.append({"text": m.group(0), "date": _build_date(m, today)})
        except ValueError:
            found.append({"text": m.group(0), "date": None})   # invalid date
    return found


def format_date(d, today=None):
    """date -> 'October 8' (adds the year if it is not the current year)."""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    today = today or date.today()
    base = f"{d:%B} {d.day}"
    return base if d.year == today.year else f"{base}, {d.year}"


def parse_bare_number(text):
    """'2' / 'two' / '2 days' -> 2. Only accepts a message that is just a number."""
    m = re.fullmatch(rf"\s*(\d{{1,3}}|{NUM_WORD_RE})(?:\s+days?)?\s*[.!]?\s*", text, re.I)
    if not m:
        return None
    token = m.group(1).lower()
    return NUMBER_WORDS.get(token) or int(token)


def parse_yes_no(text):
    """Return True (yes), False (no) or None (unclear). 'No' words are checked first."""
    t = text.lower()
    if re.search(r"\b(no|not|nope|nah|haven'?t|hasn'?t|didn'?t|pending|never)\b", t):
        return False
    if re.search(r"\b(yes|yeah|yep|yup|y|sure|done|completed|submitted|ok|okay|have|did)\b", t):
        return True
    return None


def ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
