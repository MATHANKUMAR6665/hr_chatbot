from app.chatbot import chat

EMP = "EMP101"
def say(msg, emp=EMP):
    return chat(emp, msg)


def test_greeting_small_talk():
    assert "HR Assistant" in say("Hi")["response"]
    assert say("how are you")["intent"] == "small_talk"

def test_leave_balance_from_database():
    r = say("What is my leave balance?")
    assert r["intent"] == "leave_balance" and "Casual Leave: 8" in r["response"]

def test_multi_turn_leave_request():
    assert "type of leave" in say("I want to apply for leave.")["response"]
    assert "start" in say("Sick leave.")["response"]
    assert "How many days" in say("October 8.")["response"]
    assert "reason" in say("2 days.")["response"]
    final = say("I'm not feeling well.")
    assert "submitted successfully" in final["response"] and final["flow"] is None

def test_out_of_order_slot_filling():
    r = say("I need leave on October 8 because I'm sick")
    assert r["slots"]["leave_type"] == "sick" and r["slots"]["reason"] == "I'm sick"
    assert "How many days" in r["response"]

def test_insufficient_balance():
    say("I want sick leave"); say("October 8")
    assert "only have" in say("25 days")["response"]

def test_invalid_date():
    say("I want to apply for leave"); say("sick")
    assert "not a valid date" in say("October 45")["response"]

def test_payroll_benefits_employee_onboarding():
    assert "Net Salary: ₹38,000" in say("Show my payroll details")["response"]
    assert "30th" in say("When will I get my salary?")["response"]
    assert "Mediclaim" in say("Do I have health insurance?")["response"]
    assert "IT" in say("What is my department?")["response"]
    assert "Onboarding Status" in say("What is my onboarding status?")["response"]

def test_sentiment_empathy():
    r = say("I'm frustrated because my salary hasn't arrived.")
    assert r["sentiment"] == "negative" and "sorry" in r["response"].lower() and "Payroll" in r["response"]

def test_fallback_and_errors():
    assert "HR-related" in say("Tell me a joke")["response"]
    assert "type a message" in say("   ")["response"]
    assert "couldn't find" in say("hello", emp="EMP999")["response"]

def test_linear_onboarding_flow():
    emp = "EMP105"
    assert "ID proof" in say("I am a new employee", emp)["response"]
    assert "bank details" in say("Yes", emp)["response"]
    assert "HR orientation" in say("Yes", emp)["response"]
    assert "complete the HR orientation" in say("No", emp)["response"]

def test_non_linear_conversation():
    say("I want to apply for leave.")
    r = say("Actually, when is my salary credited?")
    assert "30th" in r["response"] and "still open" in r["response"]
    assert "What date" in say("Okay, now I want sick leave.")["response"]
