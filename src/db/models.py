"""
SQLAlchemy models for IntelliTrack persistence.

Four tables:
- Person: someone registered as a missing-person reference (Phase 4 target).
- Camera: a known camera_id, for FK integrity / readability in queries.
- Sighting: every raw match event (Re-ID cross-camera OR face match) — a full log,
  written regardless of whether it becomes an alert.
- Alert: a SUBSET of sightings that cleared the confidence floor + cooldown rule.
  Alerts reference the sighting that triggered them, not a duplicate copy of the data.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.now(timezone.utc)


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    camera_id = Column(String, unique=True, nullable=False)
    source_path = Column(String, nullable=True)

    def __repr__(self):
        return f"<Camera {self.camera_id}>"


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    reference_photo_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    def __repr__(self):
        return f"<Person {self.name}>"


class Sighting(Base):
    """
    One raw match event. sighting_type distinguishes the two kinds of matches
    this project produces:
      - 'face'  : Phase 4 face match against a registered Person
      - 'reid'  : Phase 3 cross-camera Re-ID match between two tracks
                  (no Person involved — these are unidentified people)
    """
    __tablename__ = "sightings"

    id = Column(Integer, primary_key=True)
    sighting_type = Column(String, nullable=False)

    camera_id = Column(String, nullable=False)
    track_id = Column(Integer, nullable=False)
    frame_id = Column(Integer, nullable=True)
    timestamp_sec = Column(Float, nullable=False)

    similarity = Column(Float, nullable=False)


    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)


    matched_camera_id = Column(String, nullable=True)
    matched_track_id = Column(Integer, nullable=True)

    bbox = Column(String, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    person = relationship("Person")

    def __repr__(self):
        return f"<Sighting {self.sighting_type} cam={self.camera_id} t={self.timestamp_sec:.2f}>"


class Alert(Base):
    """
    A sighting that cleared the confidence floor AND the cooldown window.
    Not every sighting becomes an alert — see src/alerts/rules.py.
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    sighting_id = Column(Integer, ForeignKey("sightings.id"), nullable=False)
    alert_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    similarity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    sighting = relationship("Sighting")

    def __repr__(self):
        return f"<Alert {self.alert_type} sim={self.similarity:.3f}>"