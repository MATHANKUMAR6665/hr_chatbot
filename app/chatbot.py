"""
chatbot.py - The brain that connects everything (one function: chat()).

Pipeline for each message:
  1. nlp.analyze()               tokens, POS, NER, sentiment
  2. entity_extractor            leave_type, dates, days ...
  3. intent_classifier           intent + confidence (low confidence -> fallback)
  4. dialogue_manager            is a multi-turn flow running? continue it
  5. intent handlers             otherwise answer from the database
  6. sentiment                   add empathy if the user sounds upset
OUTPUT : dict with the reply AND all the NLP details (shown in the NLP panel).
CONCEPT : Brings together all 20 course requirements.
"""
import logging
from datetime import datetime

from . import database as db
from . import dialogue_manager as dm
from . import responses as rs
from .entity_extractor import extract_entities
from .intent_classifier import CONFIDENCE_THRESHOLD, predict_intent
from .nlp import analyze

log = logging.getLogger("hr-chatbot")
EMPATHY_LIMIT = -0.25      # only clearly upset users get an apology
EMPATHY = "I'm sorry you're experiencing this. 😔 "
NO_EMPATHY_FOR = {"frustrated_user", "complaint", "greeting", "goodbye", "thanks", "small_talk"}
CANNED_INTENTS = {"greeting", "goodbye", "thanks", "help", "small_talk", "complaint", "frustrated_user"}


# ---------------- intent handlers: each fetches data from the DB and formats a reply ----------------
def h_leave_balance(emp, ents, negative):
    return rs.leave_balance(db.get_leave_balance(emp), ents.get("leave_type"))

def h_leave_status(emp, ents, negative):
    return rs.leave_status(db.get_leave_requests(emp))

def h_cancel_leave(emp, ents, negative):
    return rs.leave_cancelled(db.cancel_latest_leave(emp))

def h_salary_date(emp, ents, negative):
    payroll = db.get_payroll(emp)
    if negative:   # upset user: show full payroll data, not only the date
        return ("Let me help you check your payroll information.\n\n" + rs.payroll(payroll) +
                "\n\nIf your salary is not credited by the salary date, please email payroll@demo-corp.com.")
    return rs.salary_date(payroll)

def h_salary_details(emp, ents, negative):
    return rs.payroll(db.get_payroll(emp))

def h_payslip(emp, ents, negative):
    return rs.payslip(db.get_payroll(emp), db.get_employee(emp)["name"])

def h_health(emp, ents, negative):
    return rs.health_insurance(db.get_benefits(emp))

def h_pf(emp, ents, negative):
    return rs.pf(db.get_benefits(emp))

def h_benefits(emp, ents, negative):
    return rs.benefits(db.get_benefits(emp))

def h_employee(emp, ents, negative):
    return rs.profile(db.get_employee(emp))

def h_department(emp, ents, negative):
    return f"🏢 You work in the **{db.get_employee(emp)['department']}** department."

def h_designation(emp, ents, negative):
    return f"💼 Your designation is **{db.get_employee(emp)['designation']}**."

def h_onb_status(emp, ents, negative):
    return rs.onboarding_status(db.get_onboarding(emp))

def h_onb_docs(emp, ents, negative):
    return rs.ONBOARDING_DOCS

HANDLERS = {
    "leave_balance": h_leave_balance, "leave_status": h_leave_status, "cancel_leave": h_cancel_leave,
    "salary_date": h_salary_date, "salary_details": h_salary_details, "payslip": h_payslip,
    "health_insurance": h_health, "pf": h_pf, "benefits": h_benefits,
    "employee_details": h_employee, "department": h_department, "designation": h_designation,
    "onboarding_status": h_onb_status, "onboarding_documents": h_onb_docs,
}


def handle_intent(intent, emp, session, ents, negative):
    if intent == "apply_leave":
        return dm.start_leave(emp, session, ents)
    if intent == "onboarding_process":
        return dm.start_onboarding(emp, session)
    if intent in CANNED_INTENTS:
        return rs.canned(intent)
    if intent in HANDLERS:
        return HANDLERS[intent](emp, ents, negative)
    return rs.FALLBACK_TEXT


# ---------------- main function ----------------
def chat(employee_id, message):
    emp = db.clean_id(employee_id)
    text = (message or "").strip()
    result = {"response": "", "intent": "fallback", "confidence": 0.0, "entities": {}, "sentiment": "neutral",
              "sentiment_score": 0.0, "tokens": [], "pos_tags": [], "ner": [], "top_intents": [],
              "slots": dm.new_leave_slots(emp), "flow": None, "context_used": False,
              "timestamp": datetime.now().strftime("%H:%M")}
    try:
        db.get_employee(emp)                                   # invalid employee id -> EmployeeNotFound
        if not text:
            result["response"] = rs.EMPTY_TEXT
            return result

        info = analyze(text)                                   # 1. tokens, POS, NER, sentiment
        ents = extract_entities(text)                          # 2. entities
        intent, conf, top3 = predict_intent(text)              # 3. intent
        session = dm.get_session(emp)
        flow_before = session["flow"]

        reply = dm.continue_flow(emp, session, text, ents, intent, conf) if flow_before else None   # 4. context
        used_context = reply is not None
        if used_context:
            intent = "apply_leave" if flow_before == "leave" else "onboarding_process"   # inherited from context
        else:
            if conf < CONFIDENCE_THRESHOLD:                    # not sure -> fallback
                intent = "fallback"
            negative = info["sentiment_score"] <= EMPATHY_LIMIT
            reply = handle_intent(intent, emp, session, ents, negative)       # 5. answer
            if negative and intent not in NO_EMPATHY_FOR:      # 6. use sentiment
                reply = EMPATHY + reply
            if session["flow"] and intent not in ("apply_leave", "onboarding_process"):
                reply += "\n\n" + dm.reminder(emp, session)    # bring the user back to the open flow

        session["last_intent"] = intent
        session["history"] = (session["history"] + [{"user": text, "bot": reply, "intent": intent}])[-20:]
        result.update(response=reply, intent=intent, confidence=round(conf, 3), entities=ents,
                      sentiment=info["sentiment"], sentiment_score=info["sentiment_score"],
                      tokens=info["tokens"], pos_tags=info["pos_tags"], ner=info["ner"],
                      top_intents=top3, slots=session["slots"], flow=session["flow"],
                      context_used=used_context)
    except db.EmployeeNotFound:
        result["response"] = rs.invalid_employee(employee_id)
    except db.HRDatabaseError:
        log.exception("Database error")
        result["response"] = rs.DB_ERROR_TEXT
    except db.LeaveError as exc:
        result["response"] = f"⚠️ {exc}"
    except Exception:                                          # never show a stack trace to the user
        log.exception("Unexpected error")
        result["response"] = rs.GENERIC_ERROR_TEXT
    return result
