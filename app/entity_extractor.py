"""
entity_extractor.py - Pulls structured values (entities) out of a message.

WHAT : "I need 2 days sick leave from October 8" ->
       {leave_type: sick, number_of_days: 2, start_date: 2026-10-08}
WHY  : The dialogue manager fills "slots" from these entities.
HOW  : Custom regex rules + date normalization (utils.py). spaCy NER (nlp.py) is shown
       separately in the NLP panel; here we need exact, normalized values.
CONCEPT : Entities (#6), entity extraction (#6).
"""
import re
from .utils import find_dates, NUM_WORD_RE, NUMBER_WORDS

EMP_RE = re.compile(r"\bEMP\d{3,}\b", re.I)

# keyword rules for the leave type entity
LEAVE_PATTERNS = {
    "sick": re.compile(r"\b(sick|illness|ill|unwell|fever|not feeling well|feeling unwell)\b", re.I),
    "casual": re.compile(r"\bcasual\b", re.I),
    "personal": re.compile(r"\b(personal|family|wedding|marriage)\b", re.I),
}
DAYS_RE = re.compile(rf"\b(\d{{1,3}}|{NUM_WORD_RE}|an?)\s+(?:more\s+)?days?\b", re.I)
REASON_RE = re.compile(r"\b(?:because|due to|since|reason is|reason:)\s+(.+?)\s*[.!?]*$", re.I)
DEPARTMENTS = ["IT", "HR", "Finance", "Marketing", "Sales", "Operations"]
DESIGNATIONS = ["Software Developer", "Junior Developer", "HR Executive", "Accountant",
                "Marketing Executive", "Sales Executive", "Manager"]


def leave_type_matches(text):
    """List of (leave_type, regex_match) sorted by position in the text."""
    hits = []
    for leave_type, pattern in LEAVE_PATTERNS.items():
        m = pattern.search(text)
        if m:
            hits.append((leave_type, m))
    return sorted(hits, key=lambda h: h[1].start())


def extract_entities(text):
    """Return a dict with only the entities that were found."""
    ents = {}

    m = EMP_RE.search(text)
    if m:
        ents["employee_id"] = m.group(0).upper()

    hits = leave_type_matches(text)
    if hits:
        ents["leave_type"] = hits[0][0]

    m = DAYS_RE.search(text)
    if m:
        word = m.group(1).lower()
        ents["number_of_days"] = 1 if word in ("a", "an") else NUMBER_WORDS.get(word) or int(word)

    dates = find_dates(text)
    valid = [d for d in dates if d["date"]]
    if valid:
        ents["start_date"] = valid[0]["date"].isoformat()
        # "from Oct 8 to Oct 10" -> second date is the end date
        if len(valid) > 1 and re.search(r"\b(to|until|till|through)\b|-", text):
            ents["end_date"] = valid[1]["date"].isoformat()
    elif dates:                                   # a date-like text that is impossible
        ents["invalid_date"] = dates[0]["text"]

    m = REASON_RE.search(text)
    if m:
        ents["reason"] = m.group(1)

    for dept in DEPARTMENTS:
        flags = 0 if dept in ("IT", "HR") else re.I     # "IT"/"HR" must be uppercase (else matches 'it')
        if re.search(rf"\b{dept}\b", text, flags):
            ents["department"] = dept
            break
    for desig in DESIGNATIONS:
        if re.search(rf"\b{desig}\b", text, re.I):
            ents["designation"] = desig
            break
    return ents
