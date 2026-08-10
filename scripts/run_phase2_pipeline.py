"""
Phase 2 — Multi-camera ingestion + detection + tracking.
Runs N cameras (from configs/camera_config.yaml) with round-robin frame
reading, each camera owning its own PersonTracker instance so track IDs
never leak across cameras. Writes one annotated .mp4 per camera to
data/outputs/.
"""
import argparse
import os

import cv2

from src.common.config import load_yaml_config
from src.common.device import get_device
from src.detection.detector import PersonDetector
from src.tracking.tracker import PersonTracker
from src.tracking.annotator import draw_tracks
from src.ingestion.multi_source import MultiSourceManager

OUTPUT_DIR = "data/outputs"


def build_writer(camera_id, frame_shape, fps=30):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"phase2_{camera_id}_tracked.mp4")
    h, w = frame_shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (w, h)), path


def main(display: bool):
    device = get_device()
    print(f"[Phase2] Using device: {device}")

    manager = MultiSourceManager("configs/camera_config.yaml")

    detector = PersonDetector(device=device)
    trackers = {}
    writers = {}
    frame_counts = {}

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
            annotated = draw_tracks(frame.image, tracks)

            if camera_id not in writers:
                writers[camera_id] = build_writer(camera_id, annotated.shape)
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
        print(f"[Phase2] {camera_id}: {frame_counts.get(camera_id, 0)} frames -> {out_path}")

    manager.release_all()

    if display:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true")
    args = parser.parse_args()
    main(display=args.display)