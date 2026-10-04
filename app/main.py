"""
main.py - The FastAPI web server (REST API + serves the chat page).

WHAT : Defines every endpoint (/api/chat, /api/leave/apply, /api/payroll/...).
WHY  : Browser <-> server communication; also shows "API fulfilment".
RUN  : uvicorn app.main:app --reload
CONCEPT : REST API using FastAPI (#20), API fulfilment (#18), error handling.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import database as db
from . import dialogue_manager
from .chatbot import chat
from .schemas import ChatRequest, LeaveApplyRequest

BASE_DIR = Path(__file__).resolve().parent.parent
log = logging.getLogger("hr-chatbot")


@asynccontextmanager
async def lifespan(app):
    if not db.DB_PATH.exists():                 # first run: create the demo database automatically
        from seed_database import seed
        seed()
    yield


app = FastAPI(title="HR Assistant Chatbot", version="1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ---------- friendly error handlers (no Python stack traces for the user) ----------
@app.exception_handler(db.EmployeeNotFound)
async def _not_found(request: Request, exc: db.EmployeeNotFound):
    return JSONResponse(status_code=404, content={"detail": f"Employee '{exc}' was not found."})

@app.exception_handler(db.LeaveError)
async def _leave_error(request: Request, exc: db.LeaveError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

@app.exception_handler(db.HRDatabaseError)
async def _db_error(request: Request, exc: db.HRDatabaseError):
    log.error("Database error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Database problem. Please try again later."})

@app.exception_handler(RequestValidationError)
async def _bad_request(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Invalid request. Please check the fields you sent.",
                                                  "errors": [e["loc"][-1] for e in exc.errors()]})

@app.exception_handler(Exception)
async def _unknown(request: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


# ---------- web page ----------
@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


# ---------- REST endpoints (the chatbot uses the same functions in database.py) ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/employee/{employee_id}")
def employee(employee_id: str):
    return db.get_employee(employee_id)

@app.get("/api/leave/balance/{employee_id}")
def leave_balance(employee_id: str):
    return db.get_leave_balance(employee_id)

@app.post("/api/leave/apply")
def leave_apply(req: LeaveApplyRequest):
    return db.apply_leave(req.employee_id, req.leave_type, req.start_date.isoformat(),
                          req.number_of_days, req.reason)

@app.get("/api/leave/status/{employee_id}")
def leave_status(employee_id: str):
    return db.get_leave_requests(employee_id)

@app.get("/api/payroll/{employee_id}")
def payroll(employee_id: str):
    return db.get_payroll(employee_id)

@app.get("/api/benefits/{employee_id}")
def benefits(employee_id: str):
    return db.get_benefits(employee_id)

@app.get("/api/onboarding/{employee_id}")
def onboarding(employee_id: str):
    return db.get_onboarding(employee_id)

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    return chat(req.employee_id, req.message)

@app.post("/api/chat/reset/{employee_id}")
def chat_reset(employee_id: str):
    dialogue_manager.reset_session(db.clean_id(employee_id))
    return {"status": "session cleared"}
