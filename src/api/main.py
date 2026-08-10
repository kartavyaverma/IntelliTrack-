"""
Minimal FastAPI layer to query stored sightings/alerts. This is what Phase 7's
dashboard will eventually call — built now since the DB exists now, per your
scope decision. Run with:
    uvicorn src.api.main:app --reload
"""
import os
import re
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.db.session import SessionLocal, init_db
from src.db.models import Sighting, Alert, Person, Camera
from src.db.crud import get_or_create_person
from src.common.device import get_device
from src.face_match.embedder import FaceEmbedder

app = FastAPI(title="IntelliTrack API")





app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR = "data/outputs"
os.makedirs(OUTPUTS_DIR, exist_ok=True)
app.mount("/static/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

MISSING_PERSONS_DIR = "data/missing_persons"
os.makedirs(MISSING_PERSONS_DIR, exist_ok=True)
app.mount("/static/missing_persons", StaticFiles(directory=MISSING_PERSONS_DIR), name="missing_persons")




_face_embedder = FaceEmbedder(device=str(get_device()))

init_db()


@app.get("/people")
def list_people():
    session = SessionLocal()
    try:
        people = session.query(Person).all()
        return [{
            "id": p.id, "name": p.name,
            "reference_photo_path": p.reference_photo_path,
            "photo_url": f"/static/missing_persons/{os.path.basename(p.reference_photo_path)}",
        } for p in people]
    finally:
        session.close()


@app.get("/cameras")
def list_cameras():
    session = SessionLocal()
    try:
        cams = session.query(Camera).all()
        return [{"id": c.id, "camera_id": c.camera_id, "source_path": c.source_path}
                for c in cams]
    finally:
        session.close()


@app.get("/sightings")
def list_sightings(sighting_type: str = None, camera_id: str = None, limit: int = 100):
    session = SessionLocal()
    try:
        q = session.query(Sighting)
        if sighting_type:
            q = q.filter(Sighting.sighting_type == sighting_type)
        if camera_id:
            q = q.filter(Sighting.camera_id == camera_id)
        rows = q.order_by(Sighting.id.desc()).limit(limit).all()
        return [{
            "id": s.id, "type": s.sighting_type, "camera_id": s.camera_id,
            "track_id": s.track_id, "timestamp_sec": s.timestamp_sec,
            "similarity": s.similarity, "person_id": s.person_id,
            "matched_camera_id": s.matched_camera_id, "matched_track_id": s.matched_track_id,
        } for s in rows]
    finally:
        session.close()


@app.get("/alerts")
def list_alerts(limit: int = 100):
    session = SessionLocal()
    try:
        rows = session.query(Alert).order_by(Alert.id.desc()).limit(limit).all()
        return [{
            "id": a.id, "type": a.alert_type, "message": a.message,
            "similarity": a.similarity, "created_at": a.created_at.isoformat(),
            "sighting_id": a.sighting_id,
        } for a in rows]
    finally:
        session.close()


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: int):
    session = SessionLocal()
    try:
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        s = alert.sighting
        return {
            "id": alert.id, "type": alert.alert_type, "message": alert.message,
            "similarity": alert.similarity, "created_at": alert.created_at.isoformat(),
            "sighting": {
                "camera_id": s.camera_id, "track_id": s.track_id,
                "timestamp_sec": s.timestamp_sec, "bbox": s.bbox,
            }
        }
    finally:
        session.close()


@app.get("/heatmaps")
def list_heatmaps():
    files = [f for f in os.listdir(OUTPUTS_DIR) if f.endswith("_heatmap.jpg")]
    return [
        {"filename": f, "url": f"/static/outputs/{f}"}
        for f in sorted(files)
    ]


def _safe_filename(name: str, original_filename: str) -> str:
    """
    Builds a filesystem-safe filename from a person's display name plus a
    timestamp, so two uploads with the same name don't collide or overwrite
    each other, and so arbitrary uploaded filenames can't do anything
    unexpected on disk (path traversal, odd characters, etc.).
    """
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip()) or "person"
    ext = os.path.splitext(original_filename)[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png"):
        ext = ".jpg"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_{timestamp}{ext}"


@app.post("/people")
async def register_person(name: str = Form(...), file: UploadFile = File(...)):
    """
    Registers a new missing-person reference photo. Validates a usable face
    is actually detectable BEFORE saving anything or writing to the DB —
    same validation this project's pipeline scripts already require at
    startup (see Phase 4's find_best_face.py debugging story), just applied
    here at upload time instead of at script-startup time.

    NOTE: this registers the person in the database, viewable via GET
    /people and the dashboard. It does NOT make an already-running pipeline
    pick up this reference live — pipeline scripts still load one
    hardcoded REFERENCE_PHOTO constant at their own startup. Making a
    running pipeline poll the DB for active people would be a further
    change, not implemented here.
    """
    session = SessionLocal()
    try:
        existing = session.query(Person).filter_by(name=name.strip()).first()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A person named '{name}' is already registered. Choose a different name."
            )

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        filename = _safe_filename(name, file.filename or "upload.jpg")
        save_path = os.path.join(MISSING_PERSONS_DIR, filename).replace("\\", "/")

        with open(save_path, "wb") as f:
            f.write(contents)




        import cv2
        img = cv2.imread(save_path)
        if img is None:
            os.remove(save_path)
            raise HTTPException(status_code=400, detail="Could not read uploaded image file.")

        faces = _face_embedder.detect_and_embed(img)
        if not faces:
            os.remove(save_path)
            raise HTTPException(
                status_code=422,
                detail=(
                    "No usable face detected in this photo (too small, too dark, "
                    "or no face present). Try a clearer, closer photo."
                )
            )

        person = get_or_create_person(session, name.strip(), save_path)
        return {
            "id": person.id,
            "name": person.name,
            "reference_photo_path": person.reference_photo_path,
            "photo_url": f"/static/missing_persons/{filename}",
            "det_score": faces[0]["det_score"],
        }
    finally:
        session.close()