"""
Phase 4 — Face recognition (missing person matching).
Extends Phase 3's pipeline: registers one reference photo as a "missing
person", then checks every frame across all cameras for a face matching
that reference.
"""
import argparse
import os

import cv2

from src.common.device import get_device
from src.detection.detector import PersonDetector
from src.tracking.tracker import PersonTracker
from src.tracking.annotator import draw_tracks
from src.ingestion.multi_source import MultiSourceManager
from src.face_match.embedder import FaceEmbedder
from src.face_match.matcher import FaceMatcher

OUTPUT_DIR = "data/outputs"
REFERENCE_PHOTO = "data/missing_persons/cropped_reference.jpg"
REFERENCE_NAME = "cropped_reference"
FACE_MATCH_THRESHOLD = 0.5


def build_writer(camera_id, frame_shape, fps=30):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"phase4_{camera_id}_tracked.mp4")
    h, w = frame_shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (w, h)), path


def register_reference(face_embedder: FaceEmbedder, matcher: FaceMatcher):
    ref_image = cv2.imread(REFERENCE_PHOTO)
    if ref_image is None:
        raise RuntimeError(f"Could not load reference photo: {REFERENCE_PHOTO}")

    faces = face_embedder.detect_and_embed(ref_image)
    if not faces:
        raise RuntimeError(
            f"No usable face detected in reference photo: {REFERENCE_PHOTO}"
        )

    matcher.register_reference(REFERENCE_NAME, faces[0]["embedding"])
    print(f"[Phase4] Registered reference '{REFERENCE_NAME}' "
          f"(det_score={faces[0]['det_score']:.3f})")


def main(display: bool, config_path: str):
    device = get_device()
    print(f"[Phase4] Using device: {device}")

    manager = MultiSourceManager(config_path)
    detector = PersonDetector(device=device)
    face_embedder = FaceEmbedder(device=device)
    matcher = FaceMatcher(match_threshold=FACE_MATCH_THRESHOLD)

    register_reference(face_embedder, matcher)

    trackers = {}
    writers = {}
    frame_counts = {}
    reported_matches = set()

    active_cameras = set(manager.all_camera_ids())

    while active_cameras:
        finished_this_round = []

        for camera_id in list(active_cameras):
            reader = manager.get_reader(camera_id)
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




            faces = face_embedder.detect_and_embed(frame.image)
            for face in faces:
                matches = matcher.match(face["embedding"])
                for person_name, score in matches:
                    match_key = (camera_id, person_name, frame.frame_id // 30)
                    if match_key not in reported_matches:
                        reported_matches.add(match_key)
                        print(
                            f"[Phase4] FACE MATCH  {camera_id}  "
                            f"person='{person_name}'  similarity={score:.3f}  "
                            f"at t={frame.timestamp:.2f}s  bbox={face['bbox']}"
                        )

            annotated = draw_tracks(frame.image, tracks)


            for face in faces:
                x1, y1, x2, y2 = [int(v) for v in face["bbox"]]
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)

            if camera_id not in writers:
                writers[camera_id] = build_writer(camera_id, annotated.shape, fps=reader.fps)
            writer, out_path = writers[camera_id]
            writer.write(annotated)

            frame_counts[camera_id] = frame_counts.get(camera_id, 0) + 1

            if display:
                cv2.imshow(f"IntelliTrack - {camera_id}", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    active_cameras.clear()
                    break

        for cid in finished_this_round:
            active_cameras.discard(cid)

    for camera_id, (writer, out_path) in writers.items():
        writer.release()
        print(f"[Phase4] {camera_id}: {frame_counts.get(camera_id, 0)} frames -> {out_path}")

    print(f"[Phase4] Total face matches reported: {len(reported_matches)}")

    manager.release_all()
    if display:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--config", type=str, default="configs/camera_config.yaml")
    args = parser.parse_args()
    main(display=args.display, config_path=args.config)