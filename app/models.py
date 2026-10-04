"""
models.py - Database table definitions (SQL schema).

WHAT : Holds the CREATE TABLE statements for the mock HR database.
WHY  : One place to see the whole database design (useful in a viva).
USED BY : seed_database.py (creates the tables) and database.py (reads them).
CONCEPT : Mock HR database (#17).
"""

LEAVE_TYPES = ("casual", "sick", "personal")

SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id  TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT,
    department   TEXT,
    designation  TEXT,
    joining_date TEXT,
    salary       REAL
);
CREATE TABLE IF NOT EXISTS leave_balance (
    employee_id    TEXT PRIMARY KEY,
    casual_leave   INTEGER DEFAULT 0,
    sick_leave     INTEGER DEFAULT 0,
    personal_leave INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS leave_requests (
    request_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id    TEXT NOT NULL,
    leave_type     TEXT NOT NULL,
    start_date     TEXT NOT NULL,
    end_date       TEXT NOT NULL,
    number_of_days INTEGER NOT NULL,
    reason         TEXT,
    status         TEXT DEFAULT 'Pending'
);
CREATE TABLE IF NOT EXISTS payroll (
    employee_id  TEXT PRIMARY KEY,
    basic_salary REAL,
    allowances   REAL,
    deductions   REAL,
    net_salary   REAL,
    salary_date  INTEGER
);
CREATE TABLE IF NOT EXISTS benefits (
    employee_id      TEXT PRIMARY KEY,
    health_insurance TEXT,
    pf               TEXT,
    other_benefits   TEXT
);
CREATE TABLE IF NOT EXISTS onboarding (
    employee_id    TEXT PRIMARY KEY,
    id_proof       INTEGER DEFAULT 0,
    bank_details   INTEGER DEFAULT 0,
    hr_orientation INTEGER DEFAULT 0,
    status         TEXT DEFAULT 'Pending'
);
"""
