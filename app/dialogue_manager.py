"""
dialogue_manager.py - Remembers the conversation and runs multi-turn flows.

WHAT : Keeps a SESSION per employee (current flow, collected slots, what we are waiting for)
       and runs two flows:
         * LEAVE flow       -> slot filling (non-linear: slots can come in any order)
         * ONBOARDING flow  -> linear question-by-question checklist
WHY  : A chatbot without memory cannot ask follow-up questions.
HOW  : session = {"flow", "awaiting", "slots", ...}. continue_flow() is called first for every
       message; it returns a reply, or None if the user changed topic (then chatbot.py
       handles the new intent and we remind the user of the unfinished flow).
CONCEPT : Linear flow (#12), non-linear flow (#13), slot filling (#14), multi-turn (#15), context (#16).
"""
import re
from datetime import date

from . import database as db
from . import responses
from .utils import parse_bare_number, parse_yes_no, format_date

INTERRUPT_CONF = 0.50    # how sure we must be that the user switched topic

# Intents that can interrupt a flow (answered, then we remind the user of the open flow)
_INFO_INTENTS = {"leave_balance", "leave_status", "cancel_leave", "salary_date", "salary_details", "payslip",
                 "health_insurance", "pf", "benefits", "employee_details", "department", "designation",
                 "onboarding_status", "onboarding_documents", "help", "small_talk", "goodbye"}
LEAVE_INTERRUPTS = _INFO_INTENTS | {"onboarding_process"}
ONBOARDING_INTERRUPTS = _INFO_INTENTS | {"apply_leave"}

ABORT_RE = re.compile(r"\b(never ?mind|forget it|stop|abort|cancel (this|it|the request|the process))\b", re.I)
LEAVE_ORDER = ["leave_type", "start_date", "number_of_days", "reason"]   # order we ask in
ONBOARDING_STEPS = [("id_proof", "ID proof", "Have you submitted your ID proof?"),
                    ("bank_details", "bank details", "Have you submitted your bank details?"),
                    ("hr_orientation", "HR orientation", "Have you completed your HR orientation?")]

sessions = {}     # employee_id -> session dict (kept in memory)


# ------------------------------------------------------------------ session handling
def new_leave_slots(employee_id=None):
    return {"employee_id": employee_id, "leave_type": None, "start_date": None,
            "end_date": None, "number_of_days": None, "reason": None}


def get_session(employee_id):
    if employee_id not in sessions:
        sessions[employee_id] = {"flow": None, "awaiting": None, "slots": new_leave_slots(employee_id),
                                 "onboarding_step": 0, "onboarding_answers": {},
                                 "last_intent": None, "history": []}
    return sessions[employee_id]


def reset_session(employee_id):
    sessions.pop(employee_id, None)


def reset_all_sessions():
    sessions.clear()


def _clear_leave(session, employee_id):
    session["flow"], session["awaiting"] = None, None
    session["slots"] = new_leave_slots(employee_id)


# ------------------------------------------------------------------ main entry point
def continue_flow(employee_id, session, text, ents, intent, conf):
    """Handle a message while a flow is active. Returns reply text, or None if user changed topic."""
    if ABORT_RE.search(text):
        flow = session["flow"]
        _clear_leave(session, employee_id)
        session["onboarding_step"], session["onboarding_answers"] = 0, {}
        return f"No problem, I've stopped the {'leave request' if flow == 'leave' else 'onboarding'}. How else can I help?"
    if session["flow"] == "leave":
        return _continue_leave(employee_id, session, text, ents, intent, conf)
    if session["flow"] == "onboarding":
        return _continue_onboarding(employee_id, session, text, intent, conf)
    return None


def reminder(employee_id, session):
    """One line appended after answering an interruption, to bring the user back."""
    if session["flow"] == "leave":
        return "📝 *Your leave request is still open.* " + leave_prompt(session["slots"])
    if session["flow"] == "onboarding":
        return "🚀 *Your onboarding is still open.* " + ONBOARDING_STEPS[session["onboarding_step"]][2]
    return ""


# ------------------------------------------------------------------ LEAVE FLOW (slot filling)
def leave_prompt(slots):
    lt = slots["leave_type"]
    if lt is None:
        return "What type of leave? (sick, casual or personal)"
    if slots["start_date"] is None:
        return f"What date should your {lt} leave start?"
    if slots["number_of_days"] is None:
        return "How many days of leave do you need?"
    return "Please provide the reason for your leave."


def start_leave(employee_id, session, ents):
    """User said 'apply leave'. Pre-fill any slots found in the first message (out-of-order input)."""
    resuming = session["flow"] != "leave" and any(session["slots"][k] for k in LEAVE_ORDER)
    session["flow"] = "leave"
    _fill_slots(session, ents, overwrite=True)
    return leave_next_step(employee_id, session, "Okay, let's continue your leave request. " if resuming else "Sure. ")


def _fill_slots(session, ents, overwrite=False):
    slots, awaiting, changed = session["slots"], session["awaiting"], False
    for key in ("leave_type", "start_date", "end_date", "number_of_days", "reason"):
        value = ents.get(key)
        if value is not None and (slots[key] is None or overwrite or key == awaiting):
            slots[key], changed = value, True
    if slots["start_date"] and slots["end_date"] and slots["number_of_days"] is None:
        slots["number_of_days"] = (date.fromisoformat(slots["end_date"]) - date.fromisoformat(slots["start_date"])).days + 1
    return changed


def leave_next_step(employee_id, session, prefix=""):
    """Validate the slots, then either ask for the next missing slot or submit the request."""
    slots = session["slots"]

    if slots["start_date"] and date.fromisoformat(slots["start_date"]) < date.today():
        slots["start_date"] = slots["end_date"] = None
        session["awaiting"] = "start_date"
        return "⚠️ That date is in the past. Please give a start date from today onwards."
    if slots["number_of_days"] is not None and slots["number_of_days"] < 1:
        slots["number_of_days"] = slots["end_date"] = None
        session["awaiting"] = "number_of_days"
        return "⚠️ The end date can't be before the start date. How many days of leave do you need?"

    if slots["leave_type"] and slots["number_of_days"]:                 # balance check
        available = db.get_leave_balance(employee_id)[f"{slots['leave_type']}_leave"]
        if slots["number_of_days"] > available:
            requested, kind = slots["number_of_days"], slots["leave_type"]
            slots["number_of_days"] = slots["end_date"] = None
            if available == 0:
                slots["leave_type"] = None
                session["awaiting"] = "leave_type"
                return f"⚠️ You have no {kind} leave left. Would you like a different type (sick, casual or personal)?"
            session["awaiting"] = "number_of_days"
            return (f"⚠️ You only have {available} day(s) of {kind} leave left, so I can't apply for "
                    f"{requested}. How many days (up to {available}) would you like?")

    for key in LEAVE_ORDER:
        if slots[key] is None:
            session["awaiting"] = key
            return prefix + leave_prompt(slots)

    try:                                                                # all slots filled -> API fulfilment
        result = db.apply_leave(employee_id, slots["leave_type"], slots["start_date"],
                                slots["number_of_days"], slots["reason"], slots["end_date"])
    except db.LeaveError as exc:
        slots["number_of_days"] = slots["end_date"] = None
        session["awaiting"] = "number_of_days"
        return f"⚠️ {exc} How many days would you like?"
    _clear_leave(session, employee_id)
    return responses.leave_submitted(result)


def _continue_leave(employee_id, session, text, ents, intent, conf):
    slots, awaiting = session["slots"], session["awaiting"]
    switched = intent in LEAVE_INTERRUPTS and conf >= INTERRUPT_CONF

    if awaiting == "reason":                       # any sentence is a valid reason...
        if switched:                               # ...unless the user clearly changed topic
            return None
        slots["reason"] = ents.get("reason") or text.strip()
        return leave_next_step(employee_id, session)

    if switched and len(text.split()) > 3:         # long sentence about another topic
        return None
    if ents.get("invalid_date") and not ents.get("start_date"):
        session["awaiting"] = "start_date"
        return (f"⚠️ \"{ents['invalid_date']}\" is not a valid date. "
                "Please give a real date such as October 8 or 2026-10-08.")

    changed = _fill_slots(session, ents, overwrite=(intent == "apply_leave" and conf >= INTERRUPT_CONF))
    if not changed and awaiting == "number_of_days":
        number = parse_bare_number(text)
        if number is not None:
            slots["number_of_days"], changed = number, True
    if changed:
        return leave_next_step(employee_id, session)
    if switched:
        return None
    return "Sorry, I didn't catch that. " + leave_prompt(slots) + "\n(Type 'cancel' to stop the request.)"


# ------------------------------------------------------------------ ONBOARDING FLOW (linear)
def start_onboarding(employee_id, session):
    session.update(flow="onboarding", awaiting=None, onboarding_step=0, onboarding_answers={})
    return "Welcome! 🚀 Let's complete your onboarding.\n\n" + ONBOARDING_STEPS[0][2]


def _continue_onboarding(employee_id, session, text, intent, conf):
    step = session["onboarding_step"]
    answer = parse_yes_no(text)
    if answer is None:
        if intent in ONBOARDING_INTERRUPTS and conf >= INTERRUPT_CONF:
            return None
        return "Please answer with **yes** or **no**. " + ONBOARDING_STEPS[step][2]

    session["onboarding_answers"][ONBOARDING_STEPS[step][0]] = answer
    step += 1
    session["onboarding_step"] = step
    if step < len(ONBOARDING_STEPS):
        return ONBOARDING_STEPS[step][2]

    answers = session["onboarding_answers"]                              # last question answered
    record = db.update_onboarding(employee_id, **{k: answers[k] for k, _, _ in ONBOARDING_STEPS})
    session.update(flow=None, onboarding_step=0, onboarding_answers={})
    pending = [label for key, label, _ in ONBOARDING_STEPS if not answers[key]]
    if not pending:
        return "🎉 Great! All onboarding steps are complete. Welcome aboard!\n\n" + responses.onboarding_status(record)
    return (f"Please complete the {' and '.join(pending)} before your onboarding is marked complete.\n\n"
            + responses.onboarding_status(record))
