"""
Phase 4 — Face matching against missing-person reference photos.
Given a reference photo's face embedding (extracted once at "upload" time),
checks incoming face embeddings from the pipeline for a match.
"""
import numpy as np


class FaceMatcher:
    def __init__(self, match_threshold: float = 0.5):



        self.match_threshold = match_threshold
        self.references = {}

    def register_reference(self, person_name: str, embedding: np.ndarray):
        self.references[person_name] = embedding

    def match(self, embedding: np.ndarray):
        """
        Returns list of (person_name, similarity) for every reference
        above match_threshold, sorted best-first. Empty list = no match.
        """
        results = []
        for name, ref_embedding in self.references.items():
            score = float(np.dot(embedding, ref_embedding))
            if score >= self.match_threshold:
                results.append((name, score))
        results.sort(key=lambda x: -x[1])
        return results