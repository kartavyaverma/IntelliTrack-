"""
Phase 3 — Re-ID embedding extraction.
Wraps torchreid's OSNet FeatureExtractor to turn a tracked person's
bounding-box crop into a fixed-size appearance embedding, suitable for
FAISS similarity search across cameras.
"""
import numpy as np
from torchreid.reid.utils import FeatureExtractor


class PersonEmbedder:
    def __init__(self, device: str = "cpu", model_name: str = "osnet_x1_0",
                 model_path: str = "models/osnet_x1_0_market1501.pth"):
        self.extractor = FeatureExtractor(
            model_name=model_name,
            model_path=model_path,
            device=str(device),
        )

    def embed(self, frame_image: np.ndarray, bbox) -> np.ndarray:
        """
        frame_image: raw BGR frame (as produced by VideoReader / cv2).
        bbox: [x1, y1, x2, y2] — Track's bbox format per Phase 1 contract.
        Returns a single L2-normalized embedding vector, shape (512,), dtype float32.
        """
        crop = self._crop(frame_image, bbox)
        if crop is None:
            return None


        crop_rgb = crop[:, :, ::-1]

        with_batch = [crop_rgb]
        features = self.extractor(with_batch)
        vec = features[0].detach().cpu().numpy().astype("float32")

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    @staticmethod
    def _crop(frame_image: np.ndarray, bbox):
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h, w = frame_image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame_image[y1:y2, x1:x2]