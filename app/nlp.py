"""
nlp.py - The NLP pipeline: tokenization, POS tagging, NER and sentiment.

WHAT : analyze(text) runs spaCy + VADER on every message and returns the results.
WHY  : These are the core "NLP basics" of the course and they are displayed in the
       NLP Analysis panel of the web UI.
USED BY : chatbot.py (for every message)
CONCEPT : Tokenization (#1), POS tagging (#2), NER (#3), Sentiment detection (#4).
"""
import re

import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .entity_extractor import EMP_RE, leave_type_matches

try:
    _nlp = spacy.load("en_core_web_sm")
except OSError as exc:
    raise RuntimeError("spaCy model missing. Run: python -m spacy download en_core_web_sm") from exc

_vader = SentimentIntensityAnalyzer()
NEGATIVE_LIMIT = -0.05     # VADER's standard cut-offs
POSITIVE_LIMIT = 0.05


def tokenize_and_tag(doc):
    """Tokens + part-of-speech tags, e.g. need -> VERB."""
    tokens = [t.text for t in doc if not t.is_space]
    pos_tags = [{"token": t.text, "pos": t.pos_} for t in doc if not t.is_space]
    return tokens, pos_tags


def named_entities(doc, text):
    """spaCy NER (DATE, CARDINAL...) plus two custom entity types: EMPLOYEE_ID and LEAVE_TYPE."""
    custom = [{"text": m.group(0), "label": "EMPLOYEE_ID", "span": m.span()} for m in EMP_RE.finditer(text)]
    custom += [{"text": m.group(0), "label": "LEAVE_TYPE", "span": m.span()}
               for _, m in leave_type_matches(text)]
    entities = []
    for ent in doc.ents:                                   # keep spaCy entities that don't overlap ours
        if not any(ent.start_char < c["span"][1] and c["span"][0] < ent.end_char for c in custom):
            entities.append({"text": ent.text, "label": ent.label_})
    entities += [{"text": c["text"], "label": c["label"]} for c in custom]
    return entities


# VADER thinks "leave" and "sick" are negative words, but in an HR chatbot they are just topics.
# So we hide them before scoring (a small "domain adaptation" step).
HR_NEUTRAL_WORDS = re.compile(r"\b(leaves?|sick)\b", re.I)


def sentiment(text):
    """VADER compound score -> positive / neutral / negative."""
    score = _vader.polarity_scores(HR_NEUTRAL_WORDS.sub("", text))["compound"]
    if score <= NEGATIVE_LIMIT:
        label = "negative"
    elif score >= POSITIVE_LIMIT:
        label = "positive"
    else:
        label = "neutral"
    return label, score


def analyze(text):
    doc = _nlp(text)
    tokens, pos_tags = tokenize_and_tag(doc)
    label, score = sentiment(text)
    return {"tokens": tokens, "pos_tags": pos_tags, "ner": named_entities(doc, text),
            "sentiment": label, "sentiment_score": round(score, 3)}
