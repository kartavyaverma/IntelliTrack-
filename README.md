# IntelliTrack

Cognitive cross-camera human tracking, missing-person face matching, and
crowd analytics system.

IntelliTrack is a modular pipeline that ingests one or more video sources,
detects and tracks people within each camera, re-identifies the same person
across independent cameras using appearance embeddings, matches faces
against registered missing-person reference photos, estimates crowd density,
and persists every match through a queryable API and a live web dashboard.

Each stage of the pipeline is an independently testable module with a fixed
data contract to the next stage, rather than a single monolithic script.
This allowed every component to be developed and validated in isolation
before integration, and allows multi-camera operation to be implemented as
N independent instances of the same pipeline rather than duplicated code.

---

## Features

- Person detection and single-camera tracking with stable per-person IDs
- Multi-camera ingestion with round-robin frame reading
- Cross-camera re-identification (Re-ID) using appearance embeddings and
  FAISS similarity search
- Missing-person face matching against uploaded reference photos
- Crowd density estimation and a decaying spatial heatmap per camera
- Alert generation with a confidence floor and cooldown, backed by SQLite
- A FastAPI query layer exposing sightings, alerts, cameras, people, and
  heatmap snapshots
- A React dashboard for live inspection: Alerts, filterable Sightings,
  Heatmaps, and People registration (photo upload with face-validity check)

---

## Architecture

```
[Video Sources] --> [Ingestion Layer]
                         |
                         v
                   [Detection Stage]       YOLOv8 - where are the people
                         |
                         v
                   [Tracking Stage]        DeepSORT - same person, same ID,
                         |                 within one camera
                         v
                   [Re-ID Stage]           OSNet + FAISS - same person,
                         |                 across cameras
                         v
                   [Face Match Stage]      InsightFace - does this match a
                         |                 registered missing person
                         v
                   [Alert + Persistence]   SQLite + FastAPI
                         |
                         v
                   [Dashboard]             React - live feed of alerts,
                                            sightings, heatmaps, people

Cross-cutting: [Crowd Analytics] reads tracker output directly, independent
of the Re-ID / Face stages.
```

Every arrow is a data contract. `Frame` (camera_id, frame_id, timestamp,
image) is produced once by ingestion and consumed identically by every
downstream stage. Detection produces standardized `Detection` objects;
tracking produces standardized `Track` objects. This is what allows a
detector or tracker to be swapped later without touching any other stage.

---

## Technology Stack

| Component | Library | Why |
|---|---|---|
| Detection | YOLOv8 (Ultralytics) | Real-time speed/accuracy balance, pretrained COCO weights include the person class, runs unmodified on CPU or GPU |
| Tracking | DeepSORT (deep-sort-realtime) | Kalman motion filter plus an appearance embedding; a well-documented, widely taught baseline |
| Cross-camera Re-ID | OSNet (torchreid, Market1501-pretrained) + FAISS | Lightweight Re-ID-specific embedding model; FAISS gives fast nearest-neighbour search over embeddings |
| Face recognition | InsightFace (buffalo_l) | Ships both detection and recognition models, installs cleanly via ONNX Runtime |
| Database | SQLite (SQLAlchemy) | Sufficient for a single-machine deployment with no concurrent-write requirement |
| Backend API | FastAPI | Async-capable, automatic interactive docs, type-safe request/response models |
| Frontend | React (Vite) | Fast local dev server, standard toolkit for a live data-driven dashboard |
| Video I/O | OpenCV | Standard, works with any video file, webcam, or RTSP source |

---

## Project Structure

```
intellitrack/
├── configs/
│   ├── camera_config.yaml      Default cameras (MOT17-04 + MOT17-09)
│   ├── camera_config_*.yaml    Alternate camera sets (own footage, Re-ID test, empty video)
│   └── model_config.yaml       Model/threshold configuration (read by Phase 6)
├── data/
│   ├── videos/                 Source video files
│   ├── missing_persons/        Registered reference photos
│   ├── outputs/                Annotated videos, heatmap snapshots
│   └── intellitrack.db         SQLite database
├── models/                     Downloaded pretrained checkpoints
├── src/
│   ├── common/                 Device detection, config loading
│   ├── ingestion/               VideoReader, MultiSourceManager
│   ├── detection/               PersonDetector (YOLOv8)
│   ├── tracking/                PersonTracker (DeepSORT), annotator
│   ├── reid/                    PersonEmbedder, CrossCameraMatcher
│   ├── face_match/              FaceEmbedder, FaceMatcher
│   ├── crowd_analytics/         CrowdDensityEstimator, HeatmapAccumulator
│   ├── alerts/                  Alert-promotion rules (confidence + cooldown)
│   ├── db/                      SQLAlchemy models, session, CRUD helpers
│   └── api/                     FastAPI app
├── frontend/                   React dashboard (Vite)
├── scripts/                    Pipeline entrypoints, one per phase
└── tests/
```

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js and npm
- ffmpeg (for dataset preparation)

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

Download the Re-ID checkpoint (Market1501-pretrained OSNet, required —
without it Re-ID falls back to generic ImageNet weights and produces
false-positive matches):

```bash
mkdir models
python -c "import gdown; gdown.download('https://drive.google.com/uc?id=1vduhq5DpN2q1g4fYEZfPI17MJeh9qyrA', 'models/osnet_x1_0_market1501.pth', quiet=False)"
```

InsightFace's detection/recognition models download automatically on first
use.

### Frontend

```bash
cd frontend
npm install
```

### Datasets

Pipeline scripts expect video files under `data/videos/`. Any video with
visible people works; this project was developed and validated against the
MOT17 benchmark sequences (MOT17-04, MOT17-09), converted from their native
frame-sequence format to `.mp4` via ffmpeg:

```bash
ffmpeg -framerate 30 -i path/to/MOT17-XX-FRCNN/img1/%06d.jpg \
  -c:v libx264 -pix_fmt yuv420p data/videos/mot17_XX.mp4
```

Configure sources in `configs/camera_config.yaml` (the default, two MOT17
cameras — at least two cameras are needed for cross-camera Re-ID):

```yaml
cameras:
  - camera_id: cam_1
    source: data/videos/mot17_04.mp4
  - camera_id: cam_2
    source: data/videos/mot17_09.mp4
```

Alternate camera sets live next to it and are selected with `--config`:

| File | Purpose |
|---|---|
| `camera_config_own_footage.yaml` | Your own recording (`my_real_footage.mp4`) as a single camera |
| `camera_config_reid_test.yaml` | MOT17-04 split into two overlapping halves — Re-ID true-positive test |
| `camera_config_empty_test.yaml` | A video with no people — negative test |

Thresholds and model settings (detection confidence, tracker `max_age` /
`n_init`, Re-ID and face similarity thresholds, alert floors and cooldown,
overcrowding threshold, heatmap decay) are read from
`configs/model_config.yaml` by the Phase 6 pipeline.

---

## Running the Pipelines

Each phase has its own entrypoint, retained for reference; the most
complete pipeline is Phase 6, which includes every stage.

```bash
# Single camera, detection + tracking only
python -m scripts.run_phase1_pipeline --display

# Multi-camera ingestion + detection + tracking
python -m scripts.run_phase2_pipeline --display

# Adds cross-camera Re-ID
python -m scripts.run_phase3_pipeline --display --config configs/camera_config.yaml

# Full pipeline: Re-ID + face matching + persistence + alerting
python -m scripts.run_phase5_pipeline --display

# Full pipeline plus crowd density and heatmaps
python -m scripts.run_phase6_pipeline --display --heatmap

# Same pipeline on your own footage
python -m scripts.run_phase6_pipeline --heatmap --config configs/camera_config_own_footage.yaml
```

Phase 6 matches faces against **every person registered in the database**
(register at least one through the dashboard first). Phases 4 and 5 still
use the single hardcoded `cropped_reference.jpg` they were built with.

Output: `data/outputs/phase6_<camera>_tracked.mp4` (annotated video) and
`data/outputs/phase6_<camera>_heatmap.jpg` (heatmap snapshot at the end of
the run). The video writers are released in a `finally` block, so stopping
with Ctrl+C still leaves a playable file.

All scripts accept `--config <path>` to point at an alternate camera
configuration without editing code.

---

## Dashboard

Run the API and the frontend dev server in separate terminals:

```bash
# Terminal 1
uvicorn src.api.main:app --reload

# Terminal 2
cd frontend
npm run dev
```

Open `http://localhost:5173`. Four tabs are available:

- **Alerts** — every alert that cleared the confidence floor and cooldown
- **Sightings** — every raw match event, filterable by type and camera
- **Heatmaps** — decaying foot-position heatmap snapshot per camera
- **People** — register a new missing-person reference photo (validates a
  usable face is detectable before saving), browse registered people

Registering a person through the dashboard does not update an already
running pipeline process — Phase 6 loads all registered people once at
startup. Run the pipeline again to pick up a newly registered photo.

### API Endpoints

| Endpoint | Description |
|---|---|
| `GET /sightings` | All match events (with matched person name for face sightings), filterable by `sighting_type` and `camera_id` |
| `GET /alerts` | Sightings that cleared the confidence floor + cooldown |
| `GET /alerts/{alert_id}` | Single alert with its originating sighting |
| `GET /people` | Registered missing-person references |
| `POST /people` | Register a new reference photo (multipart: `name`, `file`) |
| `GET /cameras` | Known cameras |
| `GET /heatmaps` | Available heatmap snapshot images |

---

## Validation Methodology

Every threshold and matching rule in this project was validated in both
directions: shown not to fire when it should not, and shown to fire when it
should. A rule that has only ever been observed staying silent is
ambiguous evidence, not proof of correctness — this was directly
demonstrated when an initial Re-ID threshold of 0.70 appeared to work
(zero matches on unrelated footage) but later produced 3 false-positive
matches at 0.72-0.76 similarity, showing the earlier "success" was
incomplete evidence.

This discipline surfaced two genuine defects during development:

**Incorrect pretrained weights (Phase 3).** The Re-ID model was initially
loaded without an explicit checkpoint path, silently defaulting to generic
ImageNet classification weights rather than a Re-ID-trained checkpoint.
This produced measurable false-positive matches between unrelated people.
Fixed by sourcing the correct Market1501-pretrained checkpoint; the same
test data then produced zero false positives.

**Re-ID index saturation (Phase 5).** Merging the Re-ID and face-matching
pipelines re-introduced a defect where every track was re-embedded and
re-indexed on every frame rather than once per track lifetime, saturating
the FAISS index with near-duplicate vectors and producing a continuous
stream of false matches on footage already proven to have none. Fixed by
limiting embedding to once per track lifetime, restoring the original
validated zero-false-positive result.

**Wall-clock alert cooldown (post-Phase 7 review).** The 15-second cooldown
was measured with `time.time()`. On CPU the pipeline processes footage much
slower than real time, so one person on screen produced 5 alerts within
0.9 seconds of video. The cooldown now uses each frame's video timestamp;
the same footage produces a single alert.

**Re-ID top-k filtering (post-Phase 7 review).** The matcher fetched the 5
nearest neighbours and only then discarded same-camera results, so a valid
cross-camera match was silently missed whenever the 5 nearest vectors all
came from the query's own camera. It now filters same-camera vectors before
picking the top matches.

---

## Known Limitations

- Appearance-only Re-ID can confuse two people with visually similar
  clothing; a production system would add temporal/spatial plausibility
  checks.
- Camera feeds are not timestamp-reconciled against a shared real-world
  clock.
- Video ingestion processes a finite file once; a continuous live camera
  feed would require a looping or streaming ingestion mode.
- Face detection runs on every full frame, which is slow on CPU (several
  seconds per frame pair at 1080p). Every matching frame is logged as a
  Sighting by design; only Alerts are rate-limited.
- Overcrowding events are printed to the console, not stored in the database.
- SQLite is sufficient for single-machine use but would need to be
  replaced for concurrent multi-camera writers at production scale.
- A long-lived development database can misrepresent current system
  correctness if old and new data are not distinguishable — clearing the
  database and re-running is recommended when testing after a code change
  affecting matching logic.

