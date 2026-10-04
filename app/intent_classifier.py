"""
intent_classifier.py - Decides WHAT the user wants (the "intent").

WHAT : TF-IDF (text -> numbers) + Logistic Regression (numbers -> intent), trained on
       the training phrases in data/intents.json every time the server starts.
WHY  : Simple, fast, explainable machine learning - perfect for a practical exam.
OUTPUT : intent name + confidence (probability). Low confidence => fallback.
CONCEPT : Intents (#5), training phrases (#7), fallback handling (#11).
"""
import json
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .utils import MONTHS, WEEKDAYS

INTENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "intents.json"
CONFIDENCE_THRESHOLD = 0.30        # below this we use the fallback intent

_MONTH_NAMES = "|".join(m for m in MONTHS if len(m) > 4 or m in ("june", "july", "march", "april"))
_WEEKDAY_NAMES = "|".join(WEEKDAYS)


def load_intents(path=INTENTS_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["intents"]


def preprocess(text):
    """Clean text so similar sentences look alike: lowercase, EMP101 -> empid,
    October -> monthname, 8 -> num, remove punctuation."""
    t = text.lower().replace("’", "'")
    t = re.sub(r"\bemp\d+\b", "empid", t)
    t = re.sub(rf"\b({_MONTH_NAMES})\b", "monthname", t)
    t = re.sub(rf"\b({_WEEKDAY_NAMES})\b", "weekday", t)
    t = re.sub(r"\b\d+(st|nd|rd|th)?\b", "num", t)
    t = t.replace("'", "")
    t = re.sub(r"[^a-z ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class IntentClassifier:
    def __init__(self):
        self.model = Pipeline([
            ("tfidf", TfidfVectorizer(preprocessor=preprocess, ngram_range=(1, 2), sublinear_tf=True)),
            ("clf", LogisticRegression(C=20, max_iter=2000)),
        ])
        self.train()

    def train(self):
        texts, labels = [], []
        for intent in load_intents():
            for phrase in intent["training_phrases"]:
                texts.append(phrase)
                labels.append(intent["name"])
        self.model.fit(texts, labels)

    def predict(self, text):
        """Return (best_intent, confidence, top3) for a message."""
        probs = self.model.predict_proba([text])[0]
        ranked = sorted(zip(self.model.classes_, probs), key=lambda x: -x[1])
        top3 = [{"intent": name, "confidence": round(float(p), 3)} for name, p in ranked[:3]]
        best, conf = ranked[0]
        return str(best), float(conf), top3


classifier = IntentClassifier()      # trained once when the app starts


def predict_intent(text):
    return classifier.predict(text)
