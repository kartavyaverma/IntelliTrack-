"""
Alert decision logic — the layer between "a match happened" (Sighting) and
"this is worth alerting on" (Alert). Two rules, matching the plan's Phase 5
spec:
  1. Confidence floor: similarity must be >= a minimum, independent of the
     raw matcher's own threshold (lets you alert-tune without re-tuning
     the underlying Re-ID/face threshold).
  2. Cooldown: don't alert again for the same (type, key) pair within
     COOLDOWN_SECONDS of the last alert — a person standing in frame for
     10 seconds should produce ONE alert, not 300.

Cooldown state is in-memory per pipeline run (a dict), not persisted across
runs — restarting the pipeline resets cooldowns, which is the right behavior
for this project's scope (each run is a fresh "session").
"""
import time

FACE_CONFIDENCE_FLOOR = 0.65
REID_CONFIDENCE_FLOOR = 0.85
COOLDOWN_SECONDS = 15.0

_last_alert_time = {}


def _cooldown_key(alert_type: str, camera_id: str, identity_key: str) -> str:
    return f"{alert_type}:{camera_id}:{identity_key}"


def should_alert(alert_type: str, camera_id: str, identity_key: str, similarity: float) -> bool:
    """
    identity_key: for face matches, the Person name/id.
                  for reid matches, the matched (camera_id, track_id) pair as a string.
    """
    floor = FACE_CONFIDENCE_FLOOR if alert_type == "face" else REID_CONFIDENCE_FLOOR
    if similarity < floor:
        return False

    key = _cooldown_key(alert_type, camera_id, identity_key)
    now = time.time()
    last = _last_alert_time.get(key)

    if last is not None and (now - last) < COOLDOWN_SECONDS:
        return False

    _last_alert_time[key] = now
    return True