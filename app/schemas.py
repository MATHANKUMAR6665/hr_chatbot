"""
schemas.py - Pydantic models that describe the JSON the API accepts.

WHAT : ChatRequest, LeaveApplyRequest. FastAPI validates incoming JSON against them.
WHY  : Bad input (missing fields, wrong types, days < 1) is rejected automatically.
USED BY : main.py
CONCEPT : REST API (#20), error handling for invalid API requests.
"""
from datetime import date
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    employee_id: str = Field(..., examples=["EMP101"])
    message: str = Field("", examples=["I want to apply for sick leave"])


class LeaveApplyRequest(BaseModel):
    employee_id: str
    leave_type: str = Field(..., examples=["sick"])
    start_date: date
    number_of_days: int = Field(..., ge=1, le=30)
    reason: str = Field(..., min_length=2)
