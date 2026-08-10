from ultralytics import YOLO


class Detection:
    def __init__(self, bbox, confidence, class_name):
        self.bbox = bbox
        self.confidence = confidence
        self.class_name = class_name


class PersonDetector:
    PERSON_CLASS_ID = 0

    def __init__(self, model_name: str = "yolov8n.pt", confidence: float = 0.4, device: str = "cpu"):
        self.model = YOLO(model_name)
        self.confidence = confidence
        self.device = device

    def detect(self, image) -> list[Detection]:
        results = self.model.predict(
            source=image,
            conf=self.confidence,
            classes=[self.PERSON_CLASS_ID],
            device=self.device,
            verbose=False,
        )

        detections = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            bbox_ltwh = [x1, y1, x2 - x1, y2 - y1]
            detections.append(Detection(bbox=bbox_ltwh, confidence=conf, class_name="person"))

        return detections
