# HEALORA — Smart Hospital Communication & AI Clinical Workflows

HEALORA is an enterprise-grade hospital communication and clinical decision-support platform designed to connect **Patients**, **Doctors**, and **Hospital Administrators**. It combines an AI clinical safety guardrail engine, automated symptom triage, conflict-free appointment scheduling, digital prescriptions, and HIPAA-compliant audit trails.

---

## 🌟 Key Architecture & Capabilities

### 1. Clinical AI Triage & Safety Guardrails (`app/ai/agents.py`)
- **Emergency Detection**: Evaluates red-flag life-threatening conditions (e.g. chest pain, anaphylaxis, severe shortness of breath, acute neurological deficits) and automatically classifies urgency into `EMERGENCY`, `HIGH`, `MEDIUM`, or `LOW`.
- **Department Routing**: Semantically classifies symptom complaints to specialized hospital departments (*Cardiology, Orthopedics, Neurology, Pulmonology, Dermatology, Pediatrics, Gastroenterology, General Medicine*).
- **Physician Handoff Summarizer**: Generates structured clinical intake briefs for reviewing doctors.
- **Strict Clinical Disclaimer**: Automatically enforces clinical disclaimers indicating automated evaluations are for intake and triage only.

### 2. Doctor-in-the-Loop Clinical Workflows
- Doctors review AI intake summaries, triage priority, and symptom descriptions.
- Verified medical staff issue signed clinical advice, recommendations, and emergency guidance.
- Digital prescription generation with structured medication schedules, dosages, and instructions.

### 3. Smart Scheduling & Conflict Prevention
- Slot generation based on doctor availability, working days, and slot duration.
- Real-time conflict detection preventing double-booking across overlapping time slots.

### 4. Enterprise Audit Trail & Governance
- Structured audit logging (`AuditLog`) tracking sensitive clinical actions (`USER_LOGIN`, `USER_REGISTRATION`, `VIEW_RECORD`, `BOOK_APPOINTMENT`, `ISSUE_PRESCRIPTION`).

---

## 🚀 Quickstart Guide

### 1. Environment Setup
```bash
# Activate existing virtual environment
.venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Database & Seeding
```bash
# Seed initial demo accounts and medical records
python -m app.db.init_db
```

#### Demo Accounts
| Role | Email | Password | Details |
|---|---|---|---|
| **Patient** | `patient@healora.com` | `PatientPass123!` | John Doe, O+ blood group |
| **Doctor** | `dr.sarah@healora.com` | `DoctorPass123!` | Dr. Sarah Lin, Cardiologist |
| **Doctor** | `dr.rajesh@healora.com` | `DoctorPass123!` | Dr. Rajesh Mehta, Orthopedic Surgeon |
| **Hospital Admin** | `admin@healora.com` | `AdminPass123!` | Hospital Administrator |

### 3. Run Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

- **Interactive Web Portal**: [http://localhost:8000](http://localhost:8000)
- **OpenAPI / Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Automated Test Suite

HEALORA includes a comprehensive test suite covering AI triage, authentication, appointments, and queries:

```bash
pytest -v
```

All 9 test suites run against an isolated in-memory SQLite database (`tests/conftest.py`).

---

## 📁 Project Structure

```
Healora/
├── app/
│   ├── ai/                # AI Safety Guard, Triage & Summarizer Agents
│   ├── api/v1/endpoints/  # Auth, Appointments, Queries, Doctors, Admin, Records
│   ├── core/              # Config, Security, JWT Tokens, Dependencies
│   ├── db/                # SQLAlchemy session, Base, Seed script
│   ├── models/            # User, Doctor, Patient, Appointment, Query, Audit
│   ├── schemas/           # Pydantic v2 validation models
│   ├── services/          # AuditService, NotificationService
│   └── main.py            # FastAPI Application lifecycle & routes
├── static/                # Single-page web portal (HTML, CSS, JS)
│   ├── css/styles.css     # Glassmorphic clinical UI design system
│   ├── js/app.js          # Role-switching SPA client logic
│   └── index.html         # Main application interface
├── tests/                 # Pytest test suite
│   ├── conftest.py        # Isolated test database fixtures
│   ├── test_ai_triage.py  # Emergency detection & routing tests
│   ├── test_auth.py       # JWT registration & login tests
│   ├── test_appointments.py # Booking & conflict prevention tests
│   └── test_queries.py    # Query triage & doctor response tests
├── alembic/               # Database migrations
└── requirements.txt       # Dependencies
```
