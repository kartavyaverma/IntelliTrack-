
"""
Phase 5 — Merged pipeline: multi-camera ingestion + detection + tracking +
cross-camera Re-ID + face matching + persistence + alerting.

Replaces run_phase3_pipeline.py and run_phase4_pipeline.py as the single
pipeline entrypoint going forward — both matchers now run in the same
per-frame pass instead of two separate full video reads.

Every match (Re-ID or face) is written to the DB as a Sighting, unconditionally.
A Sighting becomes an Alert only if it clears the confidence floor + cooldown
rule in src/alerts/rules.py (see that file for why).
"""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torchreid")

import argparse
import os

import cv2

from src.common.config import load_yaml_config
from src.common.device import get_device
from src.detection.detector import PersonDetector
from src.tracking.tracker import PersonTracker
from src.tracking.annotator import draw_tracks
from src.ingestion.multi_source import MultiSourceManager

from src.reid.embedder import PersonEmbedder
from src.reid.matcher import CrossCameraMatcher

from src.face_match.embedder import FaceEmbedder
from src.face_match.matcher import FaceMatcher

from src.db.session import SessionLocal, init_db
from src.db.crud import (
    get_or_create_camera, get_or_create_person,
    log_face_sighting, log_reid_sighting,
)

OUTPUT_DIR = "data/outputs"
REID_MATCH_THRESHOLD = 0.85
REFERENCE_PHOTO = "data/missing_persons/cropped_reference.jpg"
REFERENCE_NAME = "cropped_reference"


def build_writer(camera_id, frame_shape, fps=30):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"phase5_{camera_id}_tracked.mp4")
    h, w = frame_shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (w, h)), path


def bbox_to_str(bbox):
    return ",".join(f"{v:.1f}" for v in bbox)


def _find_owning_track(face_bbox, tracks):
    """
    Face detection runs on the whole frame (InsightFace does its own
    localization), so to log a face match against a track_id, we find
    which tracked person's box contains the face's center point.
    Returns None if no track claims this face (e.g. a face detected
    but the body detector missed that person this frame).
    """
    fx1, fy1, fx2, fy2 = face_bbox
    fcx, fcy = (fx1 + fx2) / 2, (fy1 + fy2) / 2
    for t in tracks:
        tx1, ty1, tx2, ty2 = t.bbox
        if tx1 <= fcx <= tx2 and ty1 <= fcy <= ty2:
            return t
    return None


def main(display: bool, config_path: str):
    print("MAIN() STARTED", flush=True)

    init_db()
    db = SessionLocal()
    print("DB INITIALIZED", flush=True)

    device = get_device()
    print(f"[Phase5] Using device: {device}", flush=True)

    manager = MultiSourceManager(config_path)
    print("MULTISOURCE MANAGER READY", flush=True)

    detector = PersonDetector(device=device)
    print("DETECTOR LOADED", flush=True)

    reid_embedder = PersonEmbedder(device=device)
    reid_matcher = CrossCameraMatcher(match_threshold=REID_MATCH_THRESHOLD)
    print("REID COMPONENTS LOADED", flush=True)

    face_embedder = FaceEmbedder(device=str(device))
    face_matcher = FaceMatcher()
    print("FACE MATCH COMPONENTS LOADED", flush=True)


    for camera_id in manager.readers.keys():
        get_or_create_camera(db, camera_id)
    print("CAMERAS REGISTERED IN DB", flush=True)


    ref_image = cv2.imread(REFERENCE_PHOTO)
    if ref_image is None:
        raise RuntimeError(f"Could not read reference photo file: {REFERENCE_PHOTO}")

    ref_faces = face_embedder.detect_and_embed(ref_image)
    if not ref_faces:
        raise RuntimeError(f"No usable face detected in reference photo: {REFERENCE_PHOTO}")

    reference_embedding = ref_faces[0]["embedding"]
    face_matcher.register_reference(REFERENCE_NAME, reference_embedding)
    person = get_or_create_person(db, REFERENCE_NAME, REFERENCE_PHOTO)
    print(f"[Phase5] Registered reference '{REFERENCE_NAME}' "
          f"(det_score={ref_faces[0]['det_score']:.3f})", flush=True)

    trackers = {}
    writers = {}
    frame_counts = {}
    reid_seen_pairs = set()
    reid_indexed_tracks = set()

    active_cameras = set(manager.readers.keys())
    print(f"ACTIVE CAMERAS: {active_cameras}", flush=True)

    while active_cameras:
        finished_this_round = []

        for camera_id in list(active_cameras):
            reader = manager.readers[camera_id]
            try:
                frame = next(reader)
            except StopIteration:
                finished_this_round.append(camera_id)
                continue

            if camera_id not in trackers:
                trackers[camera_id] = PersonTracker()
            tracker = trackers[camera_id]

            detections = detector.detect(frame.image)
            tracks = tracker.update(detections, frame.image)
            annotated = draw_tracks(frame.image, tracks)


            face_detections = face_embedder.detect_and_embed(frame.image)

            for face in face_detections:
                matches = face_matcher.match(face["embedding"])
                if not matches:
                    continue
                matched_name, similarity = matches[0]

                owning_track = _find_owning_track(face["bbox"], tracks)
                track_id_for_log = owning_track.track_id if owning_track else -1

                print(f"[Phase5] FACE MATCH  {camera_id}  person='{matched_name}'  "
                      f"similarity={similarity:.3f}  at t={frame.timestamp:.2f}s  "
                      f"bbox={face['bbox']}")
                log_face_sighting(
                    db, camera_id, track_id_for_log, frame.frame_id,
                    frame.timestamp, similarity, person,
                    bbox_to_str(face["bbox"]),
                )




            for track in tracks:
                track_key = f"{camera_id}:{track.track_id}"
                if track_key in reid_indexed_tracks:
                    continue

                bbox = track.bbox
                bbox_str = bbox_to_str(bbox)

                reid_vec = reid_embedder.embed(frame.image, bbox)
                if reid_vec is not None:
                    matches = reid_matcher.query(reid_vec, camera_id, k=5)
                    if matches:
                        similarity, meta = matches[0]
                        matched_camera_id = meta["camera_id"]
                        matched_track_id = meta["track_id"]

                        pair_key = tuple(sorted([
                            f"{camera_id}:{track.track_id}",
                            f"{matched_camera_id}:{matched_track_id}",
                        ]))
                        if pair_key not in reid_seen_pairs:
                            reid_seen_pairs.add(pair_key)
                            print(f"[Phase5] REID MATCH  {camera_id}:track{track.track_id} == "
                                  f"{matched_camera_id}:track{matched_track_id}  "
                                  f"similarity={similarity:.3f}  at t={frame.timestamp:.2f}s")
                            log_reid_sighting(
                                db, camera_id, track.track_id, frame.frame_id,
                                frame.timestamp, similarity,
                                matched_camera_id, matched_track_id, bbox_str,
                            )

                    reid_matcher.add(reid_vec, camera_id, track.track_id, frame.frame_id, frame.timestamp)
                    reid_indexed_tracks.add(track_key)
            if camera_id not in writers:
                writers[camera_id] = build_writer(camera_id, annotated.shape, fps=reader.fps)
            writer, out_path = writers[camera_id]
            writer.write(annotated)

            frame_counts[camera_id] = frame_counts.get(camera_id, 0) + 1

            if display:
                cv2.imshow(f"IntelliTrack Phase5 - {camera_id}", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    active_cameras.clear()
                    break

        for cid in finished_this_round:
            active_cameras.discard(cid)


    for camera_id, (writer, out_path) in writers.items():
        writer.release()
        print(f"[Phase5] {camera_id}: {frame_counts.get(camera_id, 0)} frames -> {out_path}")

    if display:
        cv2.destroyAllWindows()

    db.close()
    print("[Phase5] Done. Query results via: uvicorn src.api.main:app --reload")


if __name__ == "__main__":
    print("__main__ BLOCK REACHED", flush=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--config", default="configs/camera_config.yaml")
    args = parser.parse_args()
    print(f"ARGS PARSED: {args}", flush=True)
    main(display=args.display, config_path=args.config)