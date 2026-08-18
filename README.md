# BhoomiDrishti — Satellite-Based Change Detection Portal (SIH1518)

Full-stack government land-monitoring portal: FastAPI backend with a real
**Siamese Attention U-Net** ML model + **CLIP zero-shot classification** +
**GIS sensitivity-zone analysis** + **Groq-powered AI Copilot** +
React/Leaflet frontend + SQLite DB.

**Part 1** provides real satellite change detection on OSCD Sentinel-2 data.
**Part 2** adds an Intelligence Layer: activity classification, GIS overlap,
severity scoring, temporal tracking, and an AI Copilot.

## Screens

| Screen | Route | Notes |
|---|---|---|
| Login | `/login` | Role select + demo auth |
| Control Room Dashboard | `/dashboard` | Stat cards, pending cases, severity trend |
| Live Map | `/map` | Leaflet map, priority filters, case info panel |
| Alerts | `/alerts` | Full case table with status filters |
| Case File | `/case/:id` | Intelligence findings, imagery, timeline, cadastral records, officer notes, Copilot |
| Analytics & Reports | `/reports` | Resolution rate, hotspot chart, category breakdown |
| Field Verification App | `/field-app` | Mobile-frame mockup |
| Citizen Reporting App | `/citizen-app` | Mobile-frame mockup |

Demo login: any email + any password (e.g. `rajesh.patil@maharashtra.gov.in`).

## Quick Start

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Set environment variables (see backend/.env.example)
export OSCD_DATASET_ROOT=/path/to/oscd
export GROQ_API_KEY=your_key_here   # optional, for Copilot
uvicorn main:app --reload --port 8000
```

**Frontend** (separate terminal)
```bash
cd frontend
npm install
npm run dev
```

**Docker**
```bash
docker compose up --build
```

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for the full list.

| Variable | Default | Purpose |
|---|---|---|
| `OSCD_DATASET_ROOT` | `/data/oscd` | Path to OSCD dataset |
| `CLIP_MODEL_NAME` | `openai/clip-vit-base-patch32` | CLIP model for classification |
| `CLASSIFICATION_HIGH_THRESHOLD` | `0.6` | High-confidence cutoff |
| `CLASSIFICATION_MEDIUM_THRESHOLD` | `0.4` | Medium-confidence cutoff |
| `GIS_DATA_ROOT` | `data/gis` | Directory with GeoJSON layers |
| `GROQ_API_KEY` | *(none)* | Groq API key (Copilot) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq model selection |

## API Endpoints

### Core (Part 1)
- `POST /api/auth/login` — Demo login
- `GET /api/changes` — Filterable case list (sensitivity, type, priority, village, status)
- `GET /api/changes/{id}` — Full case file (timeline + notes)
- `POST /api/detect-change` — Real Siamese U-Net inference + Intelligence pipeline
- `PATCH /api/changes/{id}/status` — Update status (reviewed/dismissed/needs_review)
- `PATCH /api/changes/{id}/assign` — Reassign officer
- `POST /api/changes/{id}/notes` — Add officer field note
- `GET /api/changes/{id}/report` — Auto-generated evidence report
- `GET /api/stats/summary` — Dashboard stats
- `GET /api/analytics/summary` — Analytics breakdown
- `GET /api/timeline` — Multi-temporal change feed

### Intelligence (Part 2)
- `GET /api/cases/{id}/intelligence` — Full intelligence record (classification, GIS, severity, temporal)
- `GET /api/stats/intelligence` — Intelligence-level statistics
- `POST /api/copilot/chat` — AI Copilot (Groq-backed, tool-calling)

## Intelligence Pipeline (Part 2)

When `/api/detect-change` runs, the Intelligence Layer automatically processes each detection:

1. **CLIP Classification** — Zero-shot activity classification (construction, deforestation, mining, encroachment, other/unknown) using `openai/clip-vit-base-patch32`
2. **GIS Sensitivity Analysis** — Checks region geometry against available GeoJSON layers (forest, protected area, water body, wetland, agricultural). Gracefully handles non-georeferenced OSCD data.
3. **Severity Scoring** — Deterministic 0–100 score based on weighted factors: area, detection confidence, activity type, GIS overlap, and classification confidence. Produces human-readable priority reasons.
4. **Temporal Tracking** — Matches historical detections by spatial overlap (shapely geometry intersection) to classify trends: new, expanding, stable, reduced.
5. **Groq Copilot** — Tool-calling LLM assistant that queries the database on behalf of officers. Backend-only API key; no secrets in frontend.

All intelligence failures are non-blocking — the core detection always succeeds.

## Testing

```bash
cd backend
# Set PYTHONPATH to project root
export PYTHONPATH=/path/to/bhoomidrishti

# Run Part 2 unit tests
python -m pytest tests/

# Run Part 1 ML tests
python -m unittest backend.ml.tests.test_ml
```

## ML Training

```bash
pip install rasterio matplotlib geopandas shapely scikit-learn
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

python backend/ml/tools/inspect_dataset.py   # Inspect dataset
python backend/ml/training/train.py           # Train model
```

## Project Structure

```
bhoomidrishti/
├── backend/
│   ├── main.py                    # FastAPI routes + intelligence orchestration
│   ├── database.py                # SQLAlchemy ChangeRecord model
│   ├── intelligence_models.py     # IntelligenceRecord model (Part 2)
│   ├── schemas.py                 # Pydantic API contracts
│   ├── intelligence_schemas.py    # Part 2 API schemas
│   ├── mock_data.py               # Demo seeding only
│   ├── copilot/
│   │   ├── copilot_service.py     # Groq tool-calling orchestrator
│   │   └── tools.py               # Copilot tool definitions
│   ├── ml/
│   │   ├── models/                # Trained model weights
│   │   ├── classification/        # CLIP zero-shot classifier
│   │   ├── gis/                   # GIS sensitivity-zone analysis
│   │   ├── intelligence/          # Severity engine + temporal engine
│   │   ├── services/              # Model service + intelligence service
│   │   ├── inference/             # Siamese U-Net inference
│   │   ├── preprocessing/         # 13-band Sentinel-2 preprocessing
│   │   └── training/              # Training scripts
│   ├── tests/                     # Automated test suite
│   ├── .env.example               # Environment variable template
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/                 # Dashboard, LiveMap, CaseFile, etc.
│   │   └── components/            # CopilotWidget, Sidebar, Badge, etc.
│   └── package.json
└── docker-compose.yml
```
