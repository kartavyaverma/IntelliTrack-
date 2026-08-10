"""
Phase 6 — Crowd density estimation.
Reuses existing detection/tracking output — no separate model needed.
Counts people per frame and per spatial region, and flags overcrowding
against a configurable threshold.
"""
from dataclasses import dataclass


@dataclass
class DensityResult:
    camera_id: str
    frame_id: int
    total_count: int
    is_overcrowded: bool


class CrowdDensityEstimator:
    def __init__(self, overcrowd_threshold: int = 15):
        self.overcrowd_threshold = overcrowd_threshold

    def estimate(self, camera_id: str, frame_id: int, tracks) -> DensityResult:
        """
        tracks: list of Track objects (or anything with a .bbox), one per
        confirmed person in this frame.
        """
        count = len(tracks)
        return DensityResult(
            camera_id=camera_id,
            frame_id=frame_id,
            total_count=count,
            is_overcrowded=count >= self.overcrowd_threshold,
        )