import argparse
import os
import cv2

from src.ingestion.video_reader import VideoReader
from src.common.device import get_device
from src.detection.detector import PersonDetector
from src.tracking.tracker import PersonTracker
from src.tracking.annotator import draw_tracks


def run(video_path: str, output_path: str, display: bool):
    device = get_device()
    print(f"Running Phase 1 on device: {device}")

    detector = PersonDetector(device=str(device))
    tracker = PersonTracker()

    reader = VideoReader(camera_id="cam_1", source=video_path)

    first_frame = reader.read()
    if first_frame is None:
        raise RuntimeError(f"Could not read any frames from {video_path}")

    height, width = first_frame.image.shape[:2]
    fps = reader.capture.get(cv2.CAP_PROP_FPS) or 30

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    def process(frame):
        detections = detector.detect(frame.image)
        tracks = tracker.update(detections, frame.image)
        annotated = draw_tracks(frame.image, tracks)
        writer.write(annotated)
        if display:
            cv2.imshow("IntelliTrack Phase 1", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                return False
        return True

    frame_count = 0
    if not process(first_frame):
        reader.release()
        writer.release()
        return

    frame_count += 1
    for frame in reader:
        if not process(frame):
            break
        frame_count += 1

    writer.release()
    if display:
        cv2.destroyAllWindows()

    print(f"Processed {frame_count} frames. Annotated video saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default="data/videos/mot17_04.mp4")
    parser.add_argument("--output", default="data/outputs/phase1_tracked.mp4")
    parser.add_argument("--display", action="store_true")
    args = parser.parse_args()

    run(args.video, args.output, args.display)
