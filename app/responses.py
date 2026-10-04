"""
responses.py - Builds the "rich" reply texts (cards with emoji and bold headings).

WHAT : Takes raw database rows and formats them as friendly messages.
WHY  : Keeps wording/formatting separate from logic. The web UI turns **bold** and
       line breaks into HTML.
USED BY : chatbot.py, dialogue_manager.py
CONCEPT : Rich responses (#8), response generation.
"""
import json
import random

from .intent_classifier import INTENTS_PATH
from .utils import format_date, ordinal

with open(INTENTS_PATH, encoding="utf-8") as _f:
    _RESPONSES = {i["name"]: i["responses"] for i in json.load(_f)["intents"]}


def inr(amount):
    return f"₹{amount:,.0f}"


def canned(intent):
    """Pick a response from intents.json (used for small talk, help, fallback...)."""
    return random.choice(_RESPONSES[intent])


FALLBACK_TEXT = ("I'm sorry, I can currently help with HR-related questions such as leave, "
                 "payroll, benefits, employee information, and onboarding.")
EMPTY_TEXT = "Please type a message so I can help you. 😊 For example: \"What is my leave balance?\""
DB_ERROR_TEXT = "⚠️ I'm having trouble reaching the HR database right now. Please try again in a moment."
GENERIC_ERROR_TEXT = "⚠️ Something went wrong on my side. Please try again or rephrase your question."


def invalid_employee(employee_id):
    return (f"⚠️ I couldn't find an employee with ID **{employee_id or '(empty)'}**. "
            "Please check the ID (for example EMP101) and try again.")


def leave_balance(bal, leave_type=None):
    if leave_type:
        return f"🏖️ **Leave Balance**\n\n{leave_type.title()} Leave: {bal[leave_type + '_leave']} days"
    return ("🏖️ **Leave Balance**\n\n"
            f"Sick Leave: {bal['sick_leave']} days\n"
            f"Casual Leave: {bal['casual_leave']} days\n"
            f"Personal Leave: {bal['personal_leave']} days")


def leave_submitted(r):
    start = format_date(r["start_date"])
    plural = "s" if r["number_of_days"] > 1 else ""
    return (f"✅ Your {r['leave_type']} leave request from {start} for {r['number_of_days']} day{plural} "
            "has been submitted successfully.\n\n"
            f"**Request ID:** #{r['request_id']}\n"
            f"**Dates:** {start} to {format_date(r['end_date'])}\n"
            f"**Reason:** {r['reason']}\n"
            f"**Status:** {r['status']}\n"
            f"**Remaining {r['leave_type']} leave:** {r['remaining_balance']} day(s)")


def leave_status(requests):
    if not requests:
        return "📋 You have no leave requests yet."
    lines = ["📋 **Your Latest Leave Requests**\n"]
    for r in requests:
        lines.append(f"#{r['request_id']} - {r['leave_type'].title()}, {format_date(r['start_date'])} to "
                     f"{format_date(r['end_date'])} ({r['number_of_days']} day(s)) - **{r['status']}**")
    return "\n".join(lines)


def leave_cancelled(r):
    return (f"🗑️ Your {r['leave_type']} leave request #{r['request_id']} "
            f"({format_date(r['start_date'])}, {r['number_of_days']} day(s)) has been cancelled "
            "and the days were added back to your balance.")


def payroll(p):
    return ("💰 **Payroll Information**\n\n"
            f"Basic Salary: {inr(p['basic_salary'])}\n"
            f"Allowances: {inr(p['allowances'])}\n"
            f"Deductions: {inr(p['deductions'])}\n"
            f"Net Salary: {inr(p['net_salary'])}\n"
            f"Salary Date: {ordinal(p['salary_date'])} of every month")


def salary_date(p):
    return f"💰 Your salary is normally credited on the {ordinal(p['salary_date'])} of each month."


def payslip(p, name):
    return (f"🧾 **Payslip - {name}**\n\n"
            f"Earnings: {inr(p['basic_salary'] + p['allowances'])}\n"
            f"Deductions: {inr(p['deductions'])}\n"
            f"Net Pay: {inr(p['net_salary'])}\n\n"
            "(Demo: in a real system a PDF download link would appear here.)")


def benefits(b):
    return ("🎁 **Your Benefits**\n\n"
            f"Health Insurance: {b['health_insurance']}\n"
            f"Provident Fund: {b['pf']}\n"
            f"Other Benefits: {b['other_benefits']}")


def health_insurance(b):
    return f"🏥 **Health Insurance**\n\n{b['health_insurance']}"


def pf(b):
    return f"🏦 **Provident Fund**\n\n{b['pf']}"


def profile(e):
    return ("👨‍💼 **Employee Profile**\n\n"
            f"Name: {e['name']}\nEmployee ID: {e['employee_id']}\nEmail: {e['email']}\n"
            f"Department: {e['department']}\nDesignation: {e['designation']}\n"
            f"Joining Date: {format_date(e['joining_date'])}, {e['joining_date'][:4]}")


def onboarding_status(o):
    tick = lambda v: "✅ Done" if v else "⏳ Pending"
    return ("🚀 **Onboarding Status**\n\n"
            f"ID Proof: {tick(o['id_proof'])}\n"
            f"Bank Details: {tick(o['bank_details'])}\n"
            f"HR Orientation: {tick(o['hr_orientation'])}\n\n"
            f"Overall: **{o['status']}**")


ONBOARDING_DOCS = ("📄 **Documents Required for Onboarding**\n\n"
                   "1. ID proof (Aadhaar / PAN / Passport)\n"
                   "2. Bank account details (cancelled cheque or passbook copy)\n"
                   "3. Signed offer letter\n"
                   "4. Educational certificates\n"
                   "5. Previous employment relieving letter (if any)")
