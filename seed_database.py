"""
seed_database.py - Creates database/hr.db and inserts FAKE demo data.
Run:  python seed_database.py        (running it again resets the data)
"""
import sqlite3
from app.database import DB_PATH
from app.models import SCHEMA

# employee_id, name, email, dept, designation, joining, basic, allowances, deductions
EMPLOYEES = [
    ("EMP101", "Arun Kumar",   "arun.kumar@demo-corp.com",   "IT",        "Software Developer", "2022-06-15", 35000, 5000, 2000),
    ("EMP102", "Priya Sharma", "priya.sharma@demo-corp.com", "HR",        "HR Executive",       "2021-03-01", 40000, 6000, 2500),
    ("EMP103", "Rahul Verma",  "rahul.verma@demo-corp.com",  "Finance",   "Accountant",         "2020-09-10", 38000, 5500, 2300),
    ("EMP104", "Sneha Iyer",   "sneha.iyer@demo-corp.com",   "Marketing", "Marketing Executive","2023-01-20", 32000, 4500, 1800),
    ("EMP105", "Karthik Raja", "karthik.raja@demo-corp.com", "IT",        "Junior Developer",   "2026-09-28", 28000, 4000, 1500),
]
# casual, sick, personal
BALANCES = {"EMP101": (8, 6, 3), "EMP102": (10, 7, 4), "EMP103": (5, 4, 2), "EMP104": (9, 8, 3), "EMP105": (6, 6, 2)}
# id_proof, bank_details, hr_orientation, status  (EMP105 is the "new employee")
ONBOARDING = {"EMP101": (1, 1, 1, "Completed"), "EMP102": (1, 1, 1, "Completed"), "EMP103": (1, 1, 1, "Completed"),
              "EMP104": (1, 1, 1, "Completed"), "EMP105": (1, 0, 0, "In Progress")}


def seed():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    for t in ("employees", "leave_balance", "leave_requests", "payroll", "benefits", "onboarding"):
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.executescript(SCHEMA)
    for eid, name, email, dept, desig, join, basic, allow, ded in EMPLOYEES:
        conn.execute("INSERT INTO employees VALUES (?,?,?,?,?,?,?)", (eid, name, email, dept, desig, join, basic))
        conn.execute("INSERT INTO leave_balance VALUES (?,?,?,?)", (eid, *BALANCES[eid]))
        conn.execute("INSERT INTO payroll VALUES (?,?,?,?,?,?)", (eid, basic, allow, ded, basic + allow - ded, 30))
        pf_month = int(basic * 0.12)
        health = ("Pending - activates after onboarding" if eid == "EMP105"
                  else "Group Mediclaim - Rs 5,00,000 cover (self + family)")
        conn.execute("INSERT INTO benefits VALUES (?,?,?,?)", (
            eid, health, f"12% of basic (Rs {pf_month:,}/month employee + same by employer)",
            "Meal coupons, annual bonus, gym membership"))
        conn.execute("INSERT INTO onboarding VALUES (?,?,?,?,?)", (eid, *ONBOARDING[eid]))
    conn.executemany(
        "INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, number_of_days, reason, status)"
        " VALUES (?,?,?,?,?,?,?)",
        [("EMP101", "casual", "2026-08-12", "2026-08-13", 2, "Family function", "Approved"),
         ("EMP101", "sick", "2026-09-02", "2026-09-02", 1, "Fever", "Approved"),
         ("EMP102", "casual", "2026-09-18", "2026-09-19", 2, "Personal work", "Approved")])
    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH} with {len(EMPLOYEES)} demo employees.")


if __name__ == "__main__":
    seed()
