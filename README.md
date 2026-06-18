# CivGuard AI — Dubai Civil Defence Building Plan Review Platform

AI-powered building plan compliance review system. Two portals: Applicant (submit plans, view AI results) and Admin/DCD Officer (verify, override, track).

## Quick Start

### 1. Firebase Setup
1. Create a Firebase project at console.firebase.google.com named `civguard-ai-demo`
2. Enable: Authentication (Email/Password), Firestore, Storage, Hosting
3. Download your Firebase config and update `frontend/.env`
4. Download service account JSON → save as `backend/firebase-service-account.json`
5. Paste `firebase/firestore.rules` and `firebase/storage.rules` into Firebase Console
6. Create an officer user manually in Firebase Auth, then set their Firestore `users/{uid}.role = 'officer'`

### 2. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Copy .env and fill in your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
# Fill in frontend/.env with your Firebase config values
npm start
```

## Demo Endpoints
- `POST /analyse` — Real AI analysis (requires Anthropic API key + Firebase)
- `POST /analyse/demo?scenario=pass` — Mock approved result
- `POST /analyse/demo?scenario=fail` — Mock rejected result (3 critical failures)

## Folder Structure
```
civguard-ai/
├── frontend/          React + Tailwind — Applicant & Admin portals
├── backend/           Python FastAPI — AI pipeline + certificate generation
└── firebase/          Firestore & Storage rules
```

## Technology Stack
| Layer | Technology |
|---|---|
| Frontend | React + Tailwind CSS + React Router |
| Backend | Python FastAPI |
| AI | Claude Vision API (claude-sonnet-4-6) |
| Database | Firebase Firestore |
| Auth | Firebase Auth |
| Storage | Firebase Storage |
| PDF Processing | PyMuPDF |
| Certificates | ReportLab |
| Charts | Recharts |

## DCD Compliance Rules Checked
1. Emergency exit width (≥900 mm) — CRITICAL
2. Minimum number of exits (≥2) — CRITICAL
3. Max travel distance to exit (sprinklered ≤60m, non-sprinklered ≤45m) — CRITICAL
4. Minimum corridor width (≥1200 mm) — CRITICAL
5. Sprinkler system installation (mandatory ≥3 floors or ≥14m) — CRITICAL
6. Smoke detector coverage (≤60 m² per detector) — HIGH
7. Fire extinguisher placement (≤25m travel distance) — HIGH
8. Fire truck access road (≥4m width) — HIGH
9. Exit separation distance (≥1/3 diagonal sprinklered) — HIGH
10. Emergency lighting (min 1 lux, 1h battery) — MEDIUM
