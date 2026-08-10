"""
Phase 3 — Cross-camera Re-ID.
Extends Phase 2's multi-camera tracking: every confirmed track, each frame,
gets an OSNet appearance embedding. That embedding is checked against a
shared FAISS index of embeddings from ALL cameras. A high-similarity hit
from a DIFFERENT camera is reported as a cross-camera match.
"""
import argparse
import os

import cv2

from src.common.device import get_device
from src.detection.detector import PersonDetector
from src.tracking.tracker import PersonTracker
from src.tracking.annotator import draw_tracks
from src.ingestion.multi_source import MultiSourceManager
from src.reid.embedder import PersonEmbedder
from src.reid.matcher import CrossCameraMatcher

OUTPUT_DIR = "data/outputs"
MATCH_THRESHOLD = 0.85


def build_writer(camera_id, frame_shape, fps=30):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"phase3_{camera_id}_tracked.mp4")
    h, w = frame_shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (w, h)), path


def main(display: bool, args_config: str):
    device = get_device()
    print(f"[Phase3] Using device: {device}")

    manager = MultiSourceManager(args_config)
    detector = PersonDetector(device=device)
    embedder = PersonEmbedder(device=device)
    matcher = CrossCameraMatcher(embedding_dim=512, match_threshold=MATCH_THRESHOLD)

    trackers = {}
    writers = {}
    frame_counts = {}
    reported_pairs = set()

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

            for track in tracks:
                embedding = embedder.embed(frame.image, track.bbox)
                if embedding is None:
                    continue

                matches = matcher.query(embedding, camera_id=camera_id)
                for score, meta in matches:
                    pair_key = tuple(sorted([
                        f"{camera_id}:{track.track_id}",
                        f"{meta['camera_id']}:{meta['track_id']}",
                    ]))
                    if pair_key not in reported_pairs:
                        reported_pairs.add(pair_key)
                        print(
                            f"[Phase3] MATCH  {camera_id} ID {track.track_id}  <->  "
                            f"{meta['camera_id']} ID {meta['track_id']}  "
                            f"(similarity={score:.3f}, at t={frame.timestamp:.2f}s)"
                        )

                matcher.add(
                    embedding,
                    camera_id=camera_id,
                    track_id=track.track_id,
                    frame_id=frame.frame_id,
                    timestamp=frame.timestamp,
                )

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
        print(f"[Phase3] {camera_id}: {frame_counts.get(camera_id, 0)} frames -> {out_path}")

    print(f"[Phase3] Total cross-camera matches reported: {len(reported_pairs)}")

    manager.release_all()
    if display:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--config", type=str, default="configs/camera_config.yaml")
    args = parser.parse_args()
    main(display=args.display, args_config=args.config)