from src.common.config import load_yaml_config
from src.ingestion.video_reader import VideoReader


class MultiSourceManager:
    def __init__(self, camera_config_path: str):
        config = load_yaml_config(camera_config_path)
        self.readers: dict[str, VideoReader] = {}
        for camera in config["cameras"]:
            self.readers[camera["camera_id"]] = VideoReader(
                camera_id=camera["camera_id"],
                source=camera["source"],
            )

    def get_reader(self, camera_id: str) -> VideoReader:
        return self.readers[camera_id]

    def all_camera_ids(self) -> list[str]:
        return list(self.readers.keys())

    def release_all(self):
        for reader in self.readers.values():
            reader.release()
