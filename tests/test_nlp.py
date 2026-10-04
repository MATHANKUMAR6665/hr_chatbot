from app.nlp import analyze
from app.entity_extractor import extract_entities
from app.intent_classifier import predict_intent


def test_tokenization():
    assert analyze("I need sick leave")["tokens"] == ["I", "need", "sick", "leave"]

def test_pos_tagging():
    tags = {p["token"]: p["pos"] for p in analyze("I need sick leave")["pos_tags"]}
    assert tags["I"] == "PRON" and tags["need"] == "VERB"

def test_ner_date_and_employee_id():
    labels = {(n["text"], n["label"]) for n in analyze("Leave on October 8 for EMP101")["ner"]}
    assert ("October 8", "DATE") in labels and ("EMP101", "EMPLOYEE_ID") in labels

def test_sentiment():
    assert analyze("I'm very happy with my salary")["sentiment"] == "positive"
    assert analyze("I'm frustrated because my salary is late")["sentiment"] == "negative"
    assert analyze("How can I check my payslip?")["sentiment"] == "neutral"

def test_entities():
    e = extract_entities("I need 2 days sick leave from October 8")
    assert e["leave_type"] == "sick" and e["number_of_days"] == 2 and e["start_date"].endswith("-10-08")

def test_invalid_date_entity():
    assert "invalid_date" in extract_entities("leave on October 45")

def test_intents():
    for text, expected in [("Hi", "greeting"), ("What is my leave balance?", "leave_balance"),
                           ("When will I get my salary?", "salary_date"),
                           ("Do I have health insurance?", "health_insurance"),
                           ("What is my department?", "department"),
                           ("What is my onboarding status?", "onboarding_status")]:
        assert predict_intent(text)[0] == expected
