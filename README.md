# AI HR Assistant Chatbot

A small, fully working **HR chatbot** built for an NLP practical exam with **Python, FastAPI, SQLite, spaCy, VADER, scikit-learn and plain HTML/CSS/JS** (no Dialogflow / Rasa).

## Problem statement
Employees keep asking HR the same questions (leave balance, salary date, insurance...). A chatbot can answer these instantly and also run small processes such as applying for leave.

## Objective
Build a web chatbot that demonstrates NLP basics (tokenization, POS, NER, sentiment), conversational design (intents, entities, slot filling, context, fallback) and integration (mock database + REST API).

## Features
Small talk · 23 intents · entity extraction · leave request with **slot filling** · linear **onboarding flow** · non-linear topic switching · sentiment-aware replies · rich card replies · fallback + error handling · REST API · live **NLP Analysis panel**.

## Technologies
FastAPI (web/API) · SQLite (database) · spaCy `en_core_web_sm` (tokens, POS, NER) · VADER (sentiment) · scikit-learn TF-IDF + Logistic Regression (intents) · HTML/CSS/JS (UI).

## Architecture
```
User -> Web chat (static/) -> FastAPI (main.py) -> chatbot.chat()
   1. nlp.py                 tokens, POS, NER, sentiment
   2. entity_extractor.py    leave_type, dates, days, reason ...
   3. intent_classifier.py   TF-IDF + LogisticRegression -> intent + confidence
   4. dialogue_manager.py    session, slots, flows, context
   5. database.py            business logic on SQLite (same functions the REST API uses)
   6. responses.py           rich reply text  ->  back to the chat window
```

### File guide (what / why / who uses it / concept)
| File | What it does | Concept |
|---|---|---|
| `app/main.py` | FastAPI app, all endpoints, friendly error handlers | REST API, API fulfilment |
| `app/chatbot.py` | `chat()` runs the whole pipeline for one message | Everything together |
| `app/nlp.py` | spaCy tokens/POS/NER + VADER sentiment | NLP basics |
| `app/intent_classifier.py` | trains TF-IDF + LogReg from `data/intents.json`, returns intent + confidence | Intents, training phrases, fallback |
| `app/entity_extractor.py` + `utils.py` | regex rules + date/number normalization | Entities |
| `app/dialogue_manager.py` | sessions, leave slot filling, onboarding flow, interruptions | Slots, multi-turn, context, linear / non-linear |
| `app/database.py` + `models.py` | SQLite queries and schema | Mock HR DB, fulfilment |
| `app/responses.py` | formatted cards (🏖️ 💰 🎁 ...) | Rich responses |
| `app/schemas.py` | request validation (Pydantic) | Error handling |
| `seed_database.py` | creates `database/hr.db` with fake data | Mock database |
| `static/*` | chat UI + NLP panel | Web interface |
| `tests/*` | 24 automated tests | Testing |

## Installation
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python seed_database.py           # creates database/hr.db (also auto-created on first start)
```

## Running
```bash
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000** (API docs: http://127.0.0.1:8000/docs). Demo employee IDs: `EMP101`–`EMP105` (EMP105 is a new joiner). Run tests with `pytest`.

## NLP techniques
* **Tokenization / POS / NER** – spaCy; custom entity types `EMPLOYEE_ID` and `LEAVE_TYPE` added on top of spaCy's `DATE`.
* **Sentiment** – VADER. Used only to add empathy ("I'm sorry you're experiencing this") and to show full payroll data when the user is upset. The words *leave/sick* are hidden before scoring because VADER treats them as negative.
* **Intent classification** – preprocessing (lowercase, `EMP101→empid`, `October→monthname`, `8→num`) → TF-IDF (1-2 grams) → Logistic Regression. Confidence < 0.30 → fallback.

## Intents
greeting, goodbye, thanks, help, small_talk, fallback · apply_leave, leave_balance, leave_status, cancel_leave · salary_date, salary_details, payslip · health_insurance, pf, benefits · employee_details, department, designation · onboarding_status, onboarding_documents, onboarding_process · complaint, frustrated_user. (Training phrases, example entities and responses: `data/intents.json`.)

## Entities
employee_id, leave_type, start_date, end_date, number_of_days, reason, department, designation (dates are normalized to ISO, e.g. "October 8" → 2026-10-08).

## Dialogue flows
* **Leave (slot filling):** slots `leave_type → start_date → number_of_days → reason`. Anything given early is stored; only missing slots are asked. Checks: past dates, invalid dates, end before start, insufficient balance.
* **Onboarding (linear):** ID proof → bank details → HR orientation, then the DB is updated.
* **Non-linear:** if the user asks something else mid-flow, the bot answers it, keeps the slots, and reminds the user of the open flow. "cancel / never mind" stops a flow.
* **Context:** `sessions[employee_id]` stores flow, awaiting slot, slots, last intent and history. A short reply like "October 8" is understood because the bot knows it is waiting for `start_date`.

## Database schema
`employees(employee_id, name, email, department, designation, joining_date, salary)` ·
`leave_balance(employee_id, casual_leave, sick_leave, personal_leave)` ·
`leave_requests(request_id, employee_id, leave_type, start_date, end_date, number_of_days, reason, status)` ·
`payroll(employee_id, basic_salary, allowances, deductions, net_salary, salary_date)` ·
`benefits(employee_id, health_insurance, pf, other_benefits)` ·
`onboarding(employee_id, id_proof, bank_details, hr_orientation, status)` (extra table for the onboarding flow).

## API endpoints
| Method | URL |
|---|---|
| GET | `/api/employee/{id}` |
| GET | `/api/leave/balance/{id}` |
| POST | `/api/leave/apply` |
| GET | `/api/leave/status/{id}` |
| GET | `/api/payroll/{id}` |
| GET | `/api/benefits/{id}` |
| GET | `/api/onboarding/{id}` |
| POST | `/api/chat` (+ `/api/chat/reset/{id}`) |

`POST /api/chat` body: `{"employee_id":"EMP101","message":"I want to apply for sick leave"}` → returns `response, intent, confidence, entities, sentiment, slots, tokens, pos_tags, ner, top_intents, flow`.

## Screenshots
_(add screenshots here: chat window, NLP panel, leave flow, /docs page)_

## Demo checklist (Test cases)
| # | Type | Expected |
|---|---|---|
| 1 | `Hi` | greeting card, intent `greeting` |
| 2 | `What is my leave balance?` | 🏖️ card: Sick 6, Casual 8, Personal 3 (from DB) |
| 3 | `I want to apply for leave.` → `Sick` → `October 8` → `2 days` → `Not feeling well` | one question per slot, then "submitted successfully" with request ID |
| 4 | `When will I get my salary?` | credited on the 30th |
| 5 | `Do I have health insurance?` | 🏥 insurance details |
| 6 | `What is my department?` | IT |
| 7 | `What is my onboarding status?` (try EMP105) | ✅/⏳ checklist |
| 8 | `I'm frustrated because my salary hasn't arrived.` | apology + full 💰 payroll card, sentiment negative |
| 9 | `Tell me a joke` | fallback message |
| 10 | `I want to apply for leave` → `when is my salary credited?` → `now I want sick leave` | salary answered, leave reminder, flow resumes |
| Extra | `I need leave on October 8 because I'm sick` | leave_type, start_date, reason filled; only days asked |
| Extra | `25 days` as number of days | insufficient balance message |
| Extra | `October 45` | invalid date message |
| Extra | login as `EMP105`, `I am a new employee`, answer yes / yes / no | linear onboarding flow |
| Extra | empty message, `EMP999` | friendly errors |

## Future enhancements
Real authentication, manager approval workflow, persistent sessions (database/Redis), multilingual support (Tamil/Hindi), better NER with a custom-trained model, voice input, email notifications.

---


22. **Why not use Dialogflow or Rasa?** The exam goal is to show we understand each part, so we built intent detection, entities and dialogue management ourselves.
23. **How are dates like "October 8" handled?** `utils.find_dates` finds them with a regex, validates them (October 45 is rejected) and stores them as ISO dates (2026-10-08).
24. **Where is sentiment used?** In `chatbot.py`: if the score is below -0.25, an apology is added, and for salary questions the full payroll is shown.
