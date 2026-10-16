"""
Alert decision logic — the layer between "a match happened" (Sighting) and
"this is worth alerting on" (Alert). Two rules, matching the plan's Phase 5
spec:
  1. Confidence floor: similarity must be >= a minimum, independent of the
     raw matcher's own threshold (lets you alert-tune without re-tuning
     the underlying Re-ID/face threshold).
  2. Cooldown: don't alert again for the same (type, camera, identity) within
     COOLDOWN_SECONDS of the last alert — a person standing in frame for
     10 seconds should produce ONE alert, not 300.

The cooldown is measured in VIDEO time (the frame's timestamp), not
wall-clock time. On CPU the pipeline runs far slower than real time, so a
wall-clock cooldown let one person trigger several alerts within a single
second of footage. Keys include camera_id, and each camera's timestamps are
monotonic, so comparing video timestamps per key is consistent.

Cooldown state is in-memory per pipeline run (a dict), not persisted across
runs — restarting the pipeline resets cooldowns, which is the right behavior
for this project's scope (each run is a fresh "session").
"""

FACE_CONFIDENCE_FLOOR = 0.65
REID_CONFIDENCE_FLOOR = 0.85
COOLDOWN_SECONDS = 15.0

_last_alert_time = {}


def configure(face_confidence_floor: float = None, reid_confidence_floor: float = None,
              cooldown_seconds: float = None):
    """Override the defaults above, e.g. from configs/model_config.yaml."""
    global FACE_CONFIDENCE_FLOOR, REID_CONFIDENCE_FLOOR, COOLDOWN_SECONDS
    if face_confidence_floor is not None:
        FACE_CONFIDENCE_FLOOR = float(face_confidence_floor)
    if reid_confidence_floor is not None:
        REID_CONFIDENCE_FLOOR = float(reid_confidence_floor)
    if cooldown_seconds is not None:
        COOLDOWN_SECONDS = float(cooldown_seconds)


def _cooldown_key(alert_type: str, camera_id: str, identity_key: str) -> str:
    return f"{alert_type}:{camera_id}:{identity_key}"


def should_alert(alert_type: str, camera_id: str, identity_key: str, similarity: float,
                 event_time_sec: float) -> bool:
    """
    identity_key: for face matches, the Person name/id.
                  for reid matches, the matched (camera_id, track_id) pair as a string.
    event_time_sec: the video timestamp of the frame that produced the match.
    """
    floor = FACE_CONFIDENCE_FLOOR if alert_type == "face" else REID_CONFIDENCE_FLOOR
    if similarity < floor:
        return False

    key = _cooldown_key(alert_type, camera_id, identity_key)
    last = _last_alert_time.get(key)

    if last is not None and (event_time_sec - last) < COOLDOWN_SECONDS:
        return False

    _last_alert_time[key] = event_time_sec
    return True
