"""
Small helper functions so pipeline scripts don't write raw SQLAlchemy queries
inline — keeps run_phase6_pipeline.py readable and keeps DB access patterns
in one place (easy to point at in a viva: "here's the one place that writes
to the database").
"""
from src.db.models import Person, Camera, Sighting, Alert
from src.alerts.rules import should_alert


def get_or_create_camera(session, camera_id: str, source_path: str = None):
    cam = session.query(Camera).filter_by(camera_id=camera_id).first()
    if cam is None:
        cam = Camera(camera_id=camera_id, source_path=source_path)
        session.add(cam)
        session.commit()
    return cam


def get_or_create_person(session, name: str, reference_photo_path: str):
    person = session.query(Person).filter_by(name=name).first()
    if person is None:
        person = Person(name=name, reference_photo_path=reference_photo_path)
        session.add(person)
        session.commit()
    return person


def log_face_sighting(session, camera_id, track_id, frame_id, timestamp_sec,
                       similarity, person, bbox_str):
    sighting = Sighting(
        sighting_type="face",
        camera_id=camera_id,
        track_id=track_id,
        frame_id=frame_id,
        timestamp_sec=timestamp_sec,
        similarity=similarity,
        person_id=person.id,
        bbox=bbox_str,
    )
    session.add(sighting)
    session.commit()

    if should_alert("face", camera_id, person.name, similarity, timestamp_sec):
        alert = Alert(
            sighting_id=sighting.id,
            alert_type="face",
            similarity=similarity,
            message=(f"Face match: '{person.name}' seen on {camera_id} "
                     f"at t={timestamp_sec:.2f}s (similarity={similarity:.3f})"),
        )
        session.add(alert)
        session.commit()
        print(f"[Alerts] ALERT (face): {alert.message}")

    return sighting


def log_reid_sighting(session, camera_id, track_id, frame_id, timestamp_sec,
                       similarity, matched_camera_id, matched_track_id, bbox_str):
    sighting = Sighting(
        sighting_type="reid",
        camera_id=camera_id,
        track_id=track_id,
        frame_id=frame_id,
        timestamp_sec=timestamp_sec,
        similarity=similarity,
        matched_camera_id=matched_camera_id,
        matched_track_id=matched_track_id,
        bbox=bbox_str,
    )
    session.add(sighting)
    session.commit()

    identity_key = f"{matched_camera_id}:{matched_track_id}"
    if should_alert("reid", camera_id, identity_key, similarity, timestamp_sec):
        alert = Alert(
            sighting_id=sighting.id,
            alert_type="reid",
            similarity=similarity,
            message=(f"Cross-camera match: {camera_id}:track{track_id} == "
                     f"{matched_camera_id}:track{matched_track_id} "
                     f"at t={timestamp_sec:.2f}s (similarity={similarity:.3f})"),
        )
        session.add(alert)
        session.commit()
        print(f"[Alerts] ALERT (reid): {alert.message}")

    return sighting