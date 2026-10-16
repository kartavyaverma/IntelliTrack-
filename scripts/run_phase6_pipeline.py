"""
Phase 6 — Adds crowd density estimation + rolling heatmap on top of
Phase 5's merged Re-ID + face matching + persistence pipeline.
No new ML model — reuses the existing tracker output per frame.

Face matching checks against EVERY person currently registered in the
database, not a single hardcoded reference photo — anyone added via the
dashboard's People tab is included on the next pipeline run.

Thresholds and model settings are read from configs/model_config.yaml.
"""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torchreid")

import argparse
import os
import sys

# Ensure repository root is on sys.path when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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

from src.alerts import rules as alert_rules
from src.db.session import SessionLocal, init_db
from src.db.models import Person
from src.db.crud import get_or_create_camera, log_face_sighting, log_reid_sighting

from src.crowd_analytics.density import CrowdDensityEstimator
from src.crowd_analytics.heatmap import HeatmapAccumulator

OUTPUT_DIR = "data/outputs"
MODEL_CONFIG_PATH = "configs/model_config.yaml"


def build_writer(camera_id, frame_shape, fps=30):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"phase6_{camera_id}_tracked.mp4")
    h, w = frame_shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (w, h)), path


def bbox_to_str(bbox):
    return ",".join(f"{v:.1f}" for v in bbox)


def _find_owning_track(face_bbox, tracks):
    fx1, fy1, fx2, fy2 = face_bbox
    fcx, fcy = (fx1 + fx2) / 2, (fy1 + fy2) / 2
    for t in tracks:
        tx1, ty1, tx2, ty2 = t.bbox
        if tx1 <= fcx <= tx2 and ty1 <= fcy <= ty2:
            return t
    return None


def register_people(db, face_embedder, face_matcher):
    """
    Registers EVERY person in the database as a face-match reference.
    Returns {name: Person row}, needed to log a sighting's FK correctly.
    """
    all_people = db.query(Person).all()
    if not all_people:
        raise RuntimeError(
            "No people registered in the database. Register at least one "
            "person via the dashboard's People tab (or POST /people) before "
            "running the pipeline."
        )

    person_lookup = {}
    for person in all_people:
        person_image = cv2.imread(person.reference_photo_path)
        if person_image is None:
            print(f"[Phase6] WARNING: could not read photo for '{person.name}' "
                  f"at {person.reference_photo_path} — skipping.", flush=True)
            continue

        person_faces = face_embedder.detect_and_embed(person_image)
        if not person_faces:
            print(f"[Phase6] WARNING: no usable face in reference photo for "
                  f"'{person.name}' — skipping.", flush=True)
            continue

        face_matcher.register_reference(person.name, person_faces[0]["embedding"])
        person_lookup[person.name] = person
        print(f"[Phase6] Registered reference '{person.name}' "
              f"(det_score={person_faces[0]['det_score']:.3f})", flush=True)

    print(f"[Phase6] {len(person_lookup)}/{len(all_people)} people registered as "
          f"face-match references.", flush=True)
    return person_lookup


def main(display: bool, config_path: str, show_heatmap: bool):
    cfg = load_yaml_config(MODEL_CONFIG_PATH)
    det_cfg, trk_cfg = cfg["detection"], cfg["tracking"]
    reid_cfg, face_cfg = cfg["reid"], cfg["face_match"]
    alert_cfg, crowd_cfg = cfg["alerts"], cfg["crowd"]

    alert_rules.configure(
        face_confidence_floor=alert_cfg["face_confidence_floor"],
        reid_confidence_floor=alert_cfg["reid_confidence_floor"],
        cooldown_seconds=alert_cfg["cooldown_seconds"],
    )

    init_db()
    db = SessionLocal()

    device = get_device()
    print(f"[Phase6] Using device: {device}", flush=True)

    manager = MultiSourceManager(config_path)
    detector = PersonDetector(
        model_name=det_cfg["model_name"],
        confidence=det_cfg["confidence_threshold"],
        device=device,
    )

    reid_embedder = PersonEmbedder(
        device=device, model_name=reid_cfg["model_name"], model_path=reid_cfg["model_path"],
    )
    reid_matcher = CrossCameraMatcher(match_threshold=reid_cfg["match_similarity_threshold"])

    face_embedder = FaceEmbedder(
        device=str(device),
        min_det_score=face_cfg["min_det_score"],
        min_face_size_px=face_cfg["min_face_size_px"],
    )
    face_matcher = FaceMatcher(match_threshold=face_cfg["match_similarity_threshold"])

    density_estimator = CrowdDensityEstimator(overcrowd_threshold=crowd_cfg["overcrowd_threshold"])
    heatmaps = {}

    for camera_id, reader in manager.readers.items():
        get_or_create_camera(db, camera_id, reader.source)

    person_lookup = register_people(db, face_embedder, face_matcher)

    trackers = {}
    writers = {}
    frame_counts = {}
    reid_seen_pairs = set()
    reid_indexed_tracks = set()
    overcrowd_events = {}

    active_cameras = set(manager.readers.keys())

    # try/finally so the MP4 writers are always released: an MP4 only gets
    # its index (moov atom) on release(), so a Ctrl+C mid-run used to leave
    # an unplayable file behind.
    try:
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
                    trackers[camera_id] = PersonTracker(
                        max_age=trk_cfg["max_age"], n_init=trk_cfg["n_init"],
                    )
                tracker = trackers[camera_id]

                detections = detector.detect(frame.image)
                tracks = tracker.update(detections, frame.image)
                annotated = draw_tracks(frame.image, tracks)

                if camera_id not in heatmaps:
                    heatmaps[camera_id] = HeatmapAccumulator(
                        frame.image.shape, decay=crowd_cfg["heatmap_decay"],
                    )
                heatmaps[camera_id].update(tracks)

                density = density_estimator.estimate(camera_id, frame.frame_id, tracks)
                was_overcrowded = overcrowd_events.get(camera_id, False)
                if density.is_overcrowded and not was_overcrowded:
                    print(f"[Phase6] OVERCROWDING START  {camera_id}  "
                          f"count={density.total_count}  at t={frame.timestamp:.2f}s", flush=True)
                elif not density.is_overcrowded and was_overcrowded:
                    print(f"[Phase6] OVERCROWDING END  {camera_id}  "
                          f"count={density.total_count}  at t={frame.timestamp:.2f}s", flush=True)
                overcrowd_events[camera_id] = density.is_overcrowded

                if show_heatmap:
                    annotated = heatmaps[camera_id].render_overlay(annotated)

                if person_lookup:
                    face_detections = face_embedder.detect_and_embed(frame.image)
                else:
                    face_detections = []
                for face in face_detections:
                    matches = face_matcher.match(face["embedding"])
                    if not matches:
                        continue
                    matched_name, similarity = matches[0]
                    owning_track = _find_owning_track(face["bbox"], tracks)
                    track_id_for_log = owning_track.track_id if owning_track else -1

                    print(f"[Phase6] FACE MATCH  {camera_id}  person='{matched_name}'  "
                          f"similarity={similarity:.3f}  at t={frame.timestamp:.2f}s", flush=True)
                    log_face_sighting(
                        db, camera_id, track_id_for_log, frame.frame_id,
                        frame.timestamp, similarity, person_lookup[matched_name],
                        bbox_to_str(face["bbox"]),
                    )

                # Re-ID: embed each track ONCE per lifetime (embedding every
                # frame saturated the FAISS index — see README).
                for track in tracks:
                    track_key = f"{camera_id}:{track.track_id}"
                    if track_key in reid_indexed_tracks:
                        continue

                    bbox_str = bbox_to_str(track.bbox)
                    reid_vec = reid_embedder.embed(frame.image, track.bbox)
                    if reid_vec is None:
                        continue

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
                            print(f"[Phase6] REID MATCH  {camera_id}:track{track.track_id} == "
                                  f"{matched_camera_id}:track{matched_track_id}  "
                                  f"similarity={similarity:.3f}  at t={frame.timestamp:.2f}s",
                                  flush=True)
                            log_reid_sighting(
                                db, camera_id, track.track_id, frame.frame_id,
                                frame.timestamp, similarity,
                                matched_camera_id, matched_track_id, bbox_str,
                            )
                    reid_matcher.add(reid_vec, camera_id, track.track_id, frame.frame_id, frame.timestamp)
                    reid_indexed_tracks.add(track_key)

                if camera_id not in writers:
                    writers[camera_id] = build_writer(camera_id, annotated.shape, fps=reader.fps)
                writer, _ = writers[camera_id]
                writer.write(annotated)

                frame_counts[camera_id] = frame_counts.get(camera_id, 0) + 1

                if display:
                    cv2.imshow(f"IntelliTrack Phase6 - {camera_id}", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        active_cameras.clear()
                        break

            for cid in finished_this_round:
                active_cameras.discard(cid)
    finally:
        for camera_id, (writer, out_path) in writers.items():
            writer.release()
            print(f"[Phase6] {camera_id}: {frame_counts.get(camera_id, 0)} frames -> {out_path}")

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        for camera_id, hm in heatmaps.items():
            blank = (hm.accumulator * 0).astype("uint8")
            blank_bgr = cv2.cvtColor(blank, cv2.COLOR_GRAY2BGR)
            overlay = hm.render_overlay(blank_bgr)
            heatmap_path = os.path.join(OUTPUT_DIR, f"phase6_{camera_id}_heatmap.jpg")
            cv2.imwrite(heatmap_path, overlay)
            print(f"[Phase6] Saved heatmap snapshot: {heatmap_path}")

        manager.release_all()
        if display:
            cv2.destroyAllWindows()
        db.close()

    print("[Phase6] Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--config", default="configs/camera_config.yaml")
    parser.add_argument("--heatmap", action="store_true",
                        help="Overlay live heatmap on the displayed/written video")
    args = parser.parse_args()
    main(display=args.display, config_path=args.config, show_heatmap=args.heatmap)
