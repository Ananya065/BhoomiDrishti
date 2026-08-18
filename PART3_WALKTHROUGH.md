# PART 3 — FINAL WALKTHROUGH

This document outlines the final capabilities added in Part 3 and how to test them.

### 1. Dynamic Sensor Execution
**What changed:** The system now theoretically supports both `Sentinel-2` (13-band, 10m resolution) and `LISS-4` (3-band, 5.8m resolution) via abstract adapters.
**How to test:** 
- In your API client, send a `POST /api/detect-change` request.
- Add `"sensor": "liss4"` to the JSON body.
- You will receive a `500 Internal Server Error` containing the honest message: `LISS-4 model checkpoint not configured.`

### 2. Temporal Timeline Verification
**What changed:** A brand new visual timeline is injected directly into the Case File React frontend.
**How to test:** 
- Open a case in the React dashboard.
- Observe the **"Temporal Analysis Progression"** feed on the right column. It will render dates, states, and hectare areas directly pulled from the database via the Temporal Intelligence pipeline.

### 3. Interactive Before / After Image Slider
**What changed:** The dashboard previously displayed images side-by-side. It is now a professional interactive slider.
**How to test:** 
- Open any case file in the React dashboard.
- Hover over the image comparison block. Move your mouse horizontally to slide the divider left and right to compare pixels between the `Before` and `After` states.

### 4. Live PDF Compliance Report
**What changed:** Replaces the need for a third-party reporting engine with an integrated HTML-to-PDF pipeline.
**How to test:**
- Open any case file in the React dashboard.
- Click the blue **"Export PDF Report"** button in the top right.
- This opens a new browser tab hitting the `/api/changes/{change_id}/report/html` endpoint. The endpoint triggers a native OS print dialog enabling instant save-to-PDF capability.

### 5. Dockerization Fix
**What changed:** `docker-compose.yml` was fundamentally broken for the backend container because it overwrote the `/app` folder. It now cleanly mounts only the data layers.
**How to run:**
- Start Docker daemon.
- Run `docker-compose up --build -d` in the root of the repository.
- The React application is mapped to `http://localhost:3000` and the API to `http://localhost:8000`.
