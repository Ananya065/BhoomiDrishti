# PART 2 FINAL WALKTHROUGH

## 1. Environment Setup

### Environment Variables
Copy the template to create your `.env` file:
```bash
cd backend
cp .env.example .env
```
Fill in your `OSCD_DATASET_ROOT` and optional `GROQ_API_KEY`.

### Python Virtual Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
export PYTHONPATH=$(pwd)/..  # Set Python path to project root
```

## 2. Running the Application

### Start the Backend
```bash
cd backend
uvicorn main:app --reload --port 8000
```
This runs the FastAPI server. It will lazy-load the `openai/clip-vit-base-patch32` model into memory during the first inference.

### Start the Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173`. 

## 3. Running Real OSCD Detection
You can trigger a real inference using the exposed API endpoint. This runs the Siamese Attention U-Net and then triggers the Intelligence Pipeline.

```bash
curl -X POST http://127.0.0.1:8000/api/detect-change \
-H "Content-Type: application/json" \
-d '{"location_name": "abudhabi", "latitude": 24.45, "longitude": 54.37}'
```

## 4. Testing Intelligence Modules

### Checking the Database (IntelligenceRecord)
After running a detection, query SQLite to verify the 1:1 `IntelligenceRecord`:
```bash
sqlite3 backend/bhoomidrishti.db "SELECT * FROM intelligence_records ORDER BY id DESC LIMIT 1;"
```

### Testing Temporal Engine
The temporal engine matches cases by spatial intersection (`shapely`). If you run the exact same test case twice (same `after_image_date`), it will ignore the duplicate to avoid fabricating historical trends.

### Testing GIS
The GIS engine automatically prevents parsing non-georeferenced images (like the OSCD raw pixel bounds) into spherical CRSs, avoiding geographic distortion. This outputs a safe `non_georeferenced` status.

### Testing Severity
Severity is deterministic and does not rely on LLM hallucinations. The formula automatically adjusts for missing data (e.g. `gis_overlap=None` contributes 0 to the score instead of crashing).

### Testing Copilot
If `GROQ_API_KEY` is not set, asking a question in the CaseFile Copilot widget will gracefully return:
> "Groq Copilot is currently unavailable. Please configure the GROQ_API_KEY environment variable."

## 5. Running the Test Suite
All ML and Intelligence logic is fully covered by PyTest and Unittest.

**Run Part 2 Unit Tests (GIS, Temporal, Severity):**
```bash
cd backend
python -m pytest tests/
```

**Run Part 1 Core ML Tests (Model, Padding, GeoJSON):**
```bash
cd backend
python -m unittest backend.ml.tests.test_ml
```
