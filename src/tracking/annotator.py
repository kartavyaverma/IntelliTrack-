import cv2


def draw_tracks(image, tracks):
    for track in tracks:
        x1, y1, x2, y2 = map(int, track.bbox)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"ID {track.track_id}"
        cv2.putText(image, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    return image
