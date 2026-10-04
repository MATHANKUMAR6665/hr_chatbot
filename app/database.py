"""
database.py - All SQLite access + HR business logic ("fulfilment" layer).

WHAT : Small functions: get employee, leave balance, apply/cancel leave, payroll...
WHY  : The chatbot AND the REST endpoints call the SAME functions, so answers
       always come from the database instead of being hard-coded.
USED BY : chatbot.py, dialogue_manager.py, main.py
CONCEPT : API fulfilment (#18), chatbot connected to mock DB (#19), error handling.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from .models import LEAVE_TYPES

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "hr.db"


# ----- custom errors (caught in chatbot.py / main.py and turned into friendly text) -----
class HRDatabaseError(Exception):
    """Something went wrong while talking to SQLite."""

class EmployeeNotFound(Exception):
    """Employee id does not exist."""

class LeaveError(Exception):
    """Leave request is invalid (bad type, not enough balance, ...)."""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row      # lets us read columns by name
    return conn


def _fetch_one(sql, params=()):
    try:
        with get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
    except sqlite3.Error as exc:
        raise HRDatabaseError(str(exc)) from exc


def _fetch_all(sql, params=()):
    try:
        with get_connection() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error as exc:
        raise HRDatabaseError(str(exc)) from exc


def clean_id(employee_id):
    return (employee_id or "").strip().upper()


# ---------------- employee ----------------
def get_employee(employee_id):
    emp = _fetch_one("SELECT * FROM employees WHERE employee_id = ?", (clean_id(employee_id),))
    if emp is None:
        raise EmployeeNotFound(employee_id)
    return emp


# ---------------- leave ----------------
def get_leave_balance(employee_id):
    get_employee(employee_id)  # validates the id
    return _fetch_one("SELECT * FROM leave_balance WHERE employee_id = ?", (clean_id(employee_id),))


def get_leave_requests(employee_id, limit=5):
    get_employee(employee_id)
    return _fetch_all(
        "SELECT * FROM leave_requests WHERE employee_id = ? ORDER BY request_id DESC LIMIT ?",
        (clean_id(employee_id), limit))


def apply_leave(employee_id, leave_type, start_date, number_of_days, reason, end_date=None):
    """Validate and store a leave request, deduct the balance. Dates are ISO strings."""
    eid = clean_id(employee_id)
    leave_type = (leave_type or "").lower()
    if leave_type not in LEAVE_TYPES:
        raise LeaveError(f"'{leave_type}' is not a valid leave type. Choose sick, casual or personal.")
    if not number_of_days or int(number_of_days) < 1:
        raise LeaveError("Number of days must be at least 1.")
    try:
        start = date.fromisoformat(str(start_date))
    except ValueError:
        raise LeaveError("The start date is not valid.")
    days = int(number_of_days)
    end = date.fromisoformat(str(end_date)) if end_date else start + timedelta(days=days - 1)

    column = f"{leave_type}_leave"          # safe: leave_type was validated above
    balance = get_leave_balance(eid)[column]
    if days > balance:
        raise LeaveError(f"You only have {balance} day(s) of {leave_type} leave left.")
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date,"
                " number_of_days, reason, status) VALUES (?,?,?,?,?,?, 'Pending')",
                (eid, leave_type, start.isoformat(), end.isoformat(), days, reason))
            conn.execute(f"UPDATE leave_balance SET {column} = {column} - ? WHERE employee_id = ?", (days, eid))
            request_id = cur.lastrowid
    except sqlite3.Error as exc:
        raise HRDatabaseError(str(exc)) from exc
    return {"request_id": request_id, "employee_id": eid, "leave_type": leave_type,
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "number_of_days": days, "reason": reason, "status": "Pending",
            "remaining_balance": balance - days}


def cancel_latest_leave(employee_id):
    """Cancel the newest Pending request and give the days back."""
    eid = clean_id(employee_id)
    get_employee(eid)
    req = _fetch_one("SELECT * FROM leave_requests WHERE employee_id = ? AND status = 'Pending'"
                     " ORDER BY request_id DESC LIMIT 1", (eid,))
    if req is None:
        raise LeaveError("You have no pending leave request to cancel.")
    column = f"{req['leave_type']}_leave"
    try:
        with get_connection() as conn:
            conn.execute("UPDATE leave_requests SET status = 'Cancelled' WHERE request_id = ?", (req["request_id"],))
            conn.execute(f"UPDATE leave_balance SET {column} = {column} + ? WHERE employee_id = ?",
                         (req["number_of_days"], eid))
    except sqlite3.Error as exc:
        raise HRDatabaseError(str(exc)) from exc
    req["status"] = "Cancelled"
    return req


# ---------------- payroll / benefits ----------------
def get_payroll(employee_id):
    get_employee(employee_id)
    return _fetch_one("SELECT * FROM payroll WHERE employee_id = ?", (clean_id(employee_id),))


def get_benefits(employee_id):
    get_employee(employee_id)
    return _fetch_one("SELECT * FROM benefits WHERE employee_id = ?", (clean_id(employee_id),))


# ---------------- onboarding ----------------
def get_onboarding(employee_id):
    get_employee(employee_id)
    return _fetch_one("SELECT * FROM onboarding WHERE employee_id = ?", (clean_id(employee_id),))


def update_onboarding(employee_id, id_proof, bank_details, hr_orientation):
    eid = clean_id(employee_id)
    done = all([id_proof, bank_details, hr_orientation])
    try:
        with get_connection() as conn:
            conn.execute("UPDATE onboarding SET id_proof=?, bank_details=?, hr_orientation=?, status=?"
                         " WHERE employee_id=?",
                         (int(id_proof), int(bank_details), int(hr_orientation),
                          "Completed" if done else "In Progress", eid))
    except sqlite3.Error as exc:
        raise HRDatabaseError(str(exc)) from exc
    return get_onboarding(eid)
