import argparse
import cv2
from src.common.device import device_info
from src.common.config import load_yaml_config
from src.ingestion.video_reader import VideoReader


def run(camera_config_path: str, display: bool):
    print("Device info:", device_info())

    config = load_yaml_config(camera_config_path)
    first_camera = config["cameras"][0]
    reader = VideoReader(
        camera_id=first_camera["camera_id"],
        source=first_camera["source"],
    )

    frame_count = 0
    for frame in reader:
        frame_count += 1
        if display:
            cv2.imshow(frame.camera_id, frame.image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    if display:
        cv2.destroyAllWindows()

    print(f"Camera '{first_camera['camera_id']}' read {frame_count} frames successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-config", default="configs/camera_config.yaml")
    parser.add_argument("--display", action="store_true")
    args = parser.parse_args()

    run(args.camera_config, args.display)
