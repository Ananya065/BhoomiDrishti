# BhoomiDrishti — Full-Stack Govt Portal (SIH1518)

End-to-end runnable app matching the govt-portal UI/UX design: FastAPI
backend + React/Leaflet frontend (routed, multi-screen) + SQLite DB +
Docker. **The ML model is mocked** (`backend/mock_data.py`) so the whole
stack works today, before the real Siamese/SNUNet model or the real
sensitivity-zone overlap logic exist. Swap those in later without
touching routes, DB schema, or frontend — see "Handing off to ML/Dataset
leads" below.

## Screens implemented (matches the design PDF)

| Screen | Route | Notes |
|---|---|---|
| Login | `/login` | Role select + demo auth (any password works) |
| Control Room Dashboard | `/dashboard` | Stat cards, pending cases table, 6-month trend |
| Live Map | `/map` | Leaflet map, village/priority filters, info panel |
| Alerts | `/alerts` | Full case table with status filters |
| Case File | `/case/:id` | Before/after images, timeline, cadastral records, officer notes, actions |
| Analytics & Reports | `/reports` | Resolution rate, hotspot chart, category breakdown, exec summary |
| Field Verification App | `/field-app` | Mobile-frame mockup: inspector assignments + checklist |
| Citizen Reporting App | `/citizen-app` | Mobile-frame mockup: pin-drop report flow |

Demo login: any email + any password works (e.g. `rajesh.patil@maharashtra.gov.in`).

## Run it — Option A: without Docker (fastest for local dev)

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate   # or use conda
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Visit http://localhost:8000/api/health — should return `{"status":"ok"}`.
Auto-generated API docs: http://localhost:8000/docs

**Frontend** (separate terminal)
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173/login — sign in with any email/password to reach
the dashboard, which loads 18 seeded demo cases across the map, tables, and analytics.

## Run it — Option B: Docker (matches the blueprint's deployment plan)

```bash
docker compose up --build
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## API endpoints

- `POST /api/auth/login` — demo login (no real password check yet).
- `GET /api/changes` — filterable list (sensitivity, type, priority, village, status).
- `GET /api/changes/{id}` — full case file (includes timeline + notes).
- `POST /api/detect-change` — runs (mock) detection and stores the result.
- `PATCH /api/changes/{id}/status` — reviewed / dismissed / needs_review.
- `PATCH /api/changes/{id}/assign` — reassign officer.
- `POST /api/changes/{id}/notes` — add an officer field note.
- `GET /api/changes/{id}/report` — auto-generated evidence report with disclaimer.
- `GET /api/stats/summary` — dashboard control-room stats.
- `GET /api/analytics/summary` — resolution rate, hotspots, category breakdown.
- `GET /api/timeline` — multi-temporal change feed.

SQLite persistence via SQLAlchemy (`backend/database.py`) — swap
`DATABASE_URL` for Postgres later with no other code changes.

## What's mocked and needs real implementations

| File | Currently | Replace with |
|---|---|---|
| `backend/mock_data.py: run_mock_detection()` | Random change type/confidence/area/priority | Real Siamese CNN + SNUNet decoder + classification head + severity scoring output |
| `backend/mock_data.py` zone tuples | Hardcoded fake zone names (forest/protected area/water body) | Real GeoPandas/Shapely overlap check against Bhuvan/WDPA/India-geodata boundaries |
| `before_image_url` / `after_image_url` | placehold.co placeholder images | Real Sentinel-2/LISS-4 image tile URLs or served image paths |
| `backend/mock_data.py: DEMO_LOCATIONS` | 5 hardcoded Ambegaon-taluka villages | Real parcels from the district being demoed, pulled from Dataset lead's boundary layer |
| `POST /api/auth/login` | Accepts any username/password | Real auth against the district officer roster (or defer entirely for the hackathon demo) |

## Handing off to ML/Dataset leads (Completed)

The real ML model is now integrated inside `backend/ml/`!
- The dataset was discovered as `OSCD` (13 bands) and the `SiameseUNetAttention` was modified to accept 13 channels.
- The `/api/detect-change` endpoint now uses `ModelService.predict()` to run real inferences over real Sentinel-2 satellite data, generating probability masks, spatial connected components, and properly formatted GeoJSON.
- Mocking was completely decoupled from production. `run_mock_detection` only exists for initial local database seeding.
- `FocalLoss` and `DiceLoss` were integrated.
- To train the model or test ML:
```bash
# Assuming backend/venv is active
pip install rasterio matplotlib geopandas shapely scikit-learn
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Inspect Dataset
python backend/ml/tools/inspect_dataset.py

# Run Training
python backend/ml/training/train.py

# Run Tests
python -m unittest backend.ml.tests.test_ml
```

## Project structure

```
bhoomidrishti/
├── backend/
│   ├── main.py            # FastAPI routes (auth, cases, notes, analytics)
│   ├── database.py        # SQLAlchemy models + session
│   ├── schemas.py         # Pydantic request/response contracts
│   ├── mock_data.py       # ← swap this for the real model
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Route definitions
│   │   ├── auth.jsx       # Login session context
│   │   ├── api.js         # fetch wrapper for backend endpoints
│   │   ├── layouts/
│   │   │   └── AppLayout.jsx    # Sidebar shell for authenticated pages
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── LiveMap.jsx
│   │   │   ├── Alerts.jsx
│   │   │   ├── CaseFile.jsx
│   │   │   ├── Reports.jsx
│   │   │   ├── FieldApp.jsx     # mobile-frame mockup
│   │   │   └── CitizenApp.jsx   # mobile-frame mockup
│   │   └── components/    # Sidebar, TopHeader, Badge, PhoneFrame
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```
