"""
Phase 3 — Cross-camera Re-ID matching.
Maintains a FAISS index of appearance embeddings from all cameras, and
answers "has a person who looks like this been seen on a DIFFERENT camera?"
"""
import faiss
import numpy as np


class CrossCameraMatcher:
    def __init__(self, embedding_dim: int = 512, match_threshold: float = 0.7):

        self.index = faiss.IndexFlatIP(embedding_dim)
        self.metadata = []
        self.match_threshold = match_threshold

    def add(self, embedding: np.ndarray, camera_id: str, track_id: int, frame_id: int, timestamp: float):
        self.index.add(embedding.reshape(1, -1))
        self.metadata.append({
            "camera_id": camera_id,
            "track_id": track_id,
            "frame_id": frame_id,
            "timestamp": timestamp,
        })

    def query(self, embedding: np.ndarray, camera_id: str, k: int = 5):
        """
        Search for the closest embeddings NOT from the same camera.
        Returns a list of (similarity_score, metadata) above match_threshold,
        sorted best-first.
        """
        if self.index.ntotal == 0:
            return []

        # Search the whole index, THEN drop same-camera hits. Searching only
        # the top-k first would silently miss a valid cross-camera match
        # whenever the k nearest neighbours all came from the query's own
        # camera. The index holds one vector per track, so this stays small.
        scores, indices = self.index.search(embedding.reshape(1, -1), self.index.ntotal)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if score < self.match_threshold:
                break  # results are sorted best-first
            meta = self.metadata[idx]
            if meta["camera_id"] == camera_id:
                continue
            results.append((float(score), meta))
            if len(results) >= k:
                break
        return results