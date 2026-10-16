from dataclasses import dataclass
import time
import cv2


@dataclass
class Frame:
    camera_id: str
    frame_id: int
    timestamp: float
    image: "cv2.Mat"


class VideoReader:
    def __init__(self, camera_id: str, source: str):
        self.camera_id = camera_id
        self.source = source
        self.capture = cv2.VideoCapture(source)
        self.frame_id = 0

        if not self.capture.isOpened():
            raise RuntimeError(f"Could not open source: {source}")

        # Source frame rate; used for timestamps and so output videos play
        # back at the same speed as the input (not a fixed 30 fps).
        self.fps = self.capture.get(cv2.CAP_PROP_FPS) or 30.0

    def read(self) -> Frame | None:
        success, image = self.capture.read()
        if not success:
            return None

        frame = Frame(
            camera_id=self.camera_id,
            frame_id=self.frame_id,
            timestamp=self.frame_id / self.fps,
            image=image,
        )
        self.frame_id += 1
        return frame

    def release(self):
        self.capture.release()

    def __iter__(self):
        return self

    def __next__(self) -> Frame:
        frame = self.read()
        if frame is None:
            self.release()
            raise StopIteration
        return frame
