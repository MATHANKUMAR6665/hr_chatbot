from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_employee_endpoint():
    r = client.get("/api/employee/EMP101")
    assert r.status_code == 200 and r.json()["name"] == "Arun Kumar"

def test_invalid_employee_is_404():
    r = client.get("/api/employee/EMP999")
    assert r.status_code == 404 and "not found" in r.json()["detail"]

def test_get_endpoints():
    for url in ["/api/leave/balance/EMP101", "/api/leave/status/EMP101", "/api/payroll/EMP101",
                "/api/benefits/EMP101", "/api/onboarding/EMP101"]:
        assert client.get(url).status_code == 200

def test_apply_leave_api_and_validation():
    ok = client.post("/api/leave/apply", json={"employee_id": "EMP102", "leave_type": "casual",
                     "start_date": "2030-01-10", "number_of_days": 1, "reason": "Personal work"})
    assert ok.status_code == 200 and ok.json()["status"] == "Pending"
    too_many = client.post("/api/leave/apply", json={"employee_id": "EMP102", "leave_type": "casual",
                           "start_date": "2030-01-10", "number_of_days": 20, "reason": "Trip"})
    assert too_many.status_code == 400
    assert client.post("/api/leave/apply", json={"employee_id": "EMP102"}).status_code == 422

def test_chat_endpoint():
    r = client.post("/api/chat", json={"employee_id": "EMP101", "message": "I want to apply for sick leave"})
    body = r.json()
    assert r.status_code == 200 and body["intent"] == "apply_leave" and body["slots"]["leave_type"] == "sick"
    assert "tokens" in body and "sentiment" in body

def test_chat_bad_request():
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 422
