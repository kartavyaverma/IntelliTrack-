from deep_sort_realtime.deepsort_tracker import DeepSort


class Track:
    def __init__(self, track_id, bbox):
        self.track_id = track_id
        self.bbox = bbox


class PersonTracker:
    def __init__(self, max_age: int = 30, n_init: int = 3):
        self.tracker = DeepSort(max_age=max_age, n_init=n_init)

    def update(self, detections, image) -> list[Track]:
        formatted = [(d.bbox, d.confidence, d.class_name) for d in detections]
        raw_tracks = self.tracker.update_tracks(formatted, frame=image)

        confirmed_tracks = []
        for raw_track in raw_tracks:
            if not raw_track.is_confirmed():
                continue
            x1, y1, x2, y2 = raw_track.to_ltrb()
            confirmed_tracks.append(Track(track_id=raw_track.track_id, bbox=[x1, y1, x2, y2]))

        return confirmed_tracks
