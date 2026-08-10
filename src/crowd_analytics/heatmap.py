"""
Phase 6 — Rolling heatmap of where people have been standing/walking,
accumulated over time per camera.
"""
import numpy as np
import cv2


class HeatmapAccumulator:
    def __init__(self, frame_shape, decay: float = 0.98):
        """
        frame_shape: (height, width) of the camera's frames.
        decay: multiplies the accumulator each update so old activity
        fades out over time instead of permanently saturating one spot.
        """
        h, w = frame_shape[:2]
        self.accumulator = np.zeros((h, w), dtype=np.float32)
        self.decay = decay

    def update(self, tracks):
        self.accumulator *= self.decay
        for track in tracks:
            x1, y1, x2, y2 = [int(v) for v in track.bbox]
            cx, cy = (x1 + x2) // 2, y2
            h, w = self.accumulator.shape
            cx, cy = max(0, min(w - 1, cx)), max(0, min(h - 1, cy))
            cv2.circle(self.accumulator, (cx, cy), radius=20, color=1.0, thickness=-1)

    def render_overlay(self, frame_image):
        norm = cv2.normalize(self.accumulator, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")
        heat_color = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        return cv2.addWeighted(frame_image, 0.6, heat_color, 0.4, 0)