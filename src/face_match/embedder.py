"""
Phase 4 — Face embedding extraction.
Wraps InsightFace's FaceAnalysis (buffalo_l) to detect faces in a frame
and produce normalized embeddings, with confidence and size filtering
to reject the kind of low-quality detections real CCTV footage produces.
"""
import numpy as np
from insightface.app import FaceAnalysis

MIN_DET_SCORE = 0.6
MIN_FACE_SIZE_PX = 40


class FaceEmbedder:
    def __init__(self, device: str = "cpu", det_size=(640, 640)):
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "cuda" in str(device) else ["CPUExecutionProvider"]
        self.app = FaceAnalysis(name="buffalo_l", providers=providers)
        ctx_id = 0 if "cuda" in str(device) else -1
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)

    def detect_and_embed(self, frame_image: np.ndarray):
        """
        Runs face detection + embedding on a full frame (not a pre-cropped
        person box — InsightFace does its own face localization).
        Returns a list of dicts: {bbox, embedding, det_score}, filtered to
        only faces meeting MIN_DET_SCORE and MIN_FACE_SIZE_PX.
        """
        faces = self.app.get(frame_image)
        results = []

        for face in faces:
            if face.det_score < MIN_DET_SCORE:
                continue

            x1, y1, x2, y2 = face.bbox
            width, height = x2 - x1, y2 - y1
            if width < MIN_FACE_SIZE_PX or height < MIN_FACE_SIZE_PX:
                continue

            results.append({
                "bbox": face.bbox,
                "embedding": face.normed_embedding,
                "det_score": float(face.det_score),
            })

        return results