
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from vision_layer.engine import face_engine


@dataclass
class DetectionResult:
    status: str
    message: str

    face: Optional[Any] = None
    bbox: Optional[tuple] = None
    landmarks: Optional[np.ndarray] = None
    confidence: Optional[float] = None
    crop: Optional[np.ndarray] = None

    @property
    def is_valid(self):
        return self.status == "valid"


class FaceDetector:
    def __init__(
        self,
        min_confidence=0.60,
        min_face_width=100,
        min_face_height=100
    ):
        self.min_confidence = min_confidence
        self.min_face_width = min_face_width
        self.min_face_height = min_face_height

    def detect(self, frame):
        faces = face_engine.analyze(frame)

        if len(faces) == 0:
            return DetectionResult(
                status="no_face",
                message="No face detected. Look towards the camera."
            )

        if len(faces) > 1:
            return DetectionResult(
                status="multiple_faces",
                message="Only one person should be visible."
            )

        face = faces[0]

        confidence = float(face.det_score)

        if not np.isfinite(confidence):
            return DetectionResult(
                status="invalid_detection",
                message="Invalid face detection result."
            )

        if confidence < self.min_confidence:
            return DetectionResult(
                status="low_confidence",
                message="Face detection is uncertain. Improve lighting or adjust your position.",
                confidence=confidence
            )

        height, width = frame.shape[:2]

        raw_bbox = np.asarray(face.bbox, dtype=np.float32)

        if raw_bbox.shape != (4,) or not np.all(np.isfinite(raw_bbox)):
            return DetectionResult(
                status="invalid_detection",
                message="Invalid face boundary detected."
            )

        x1, y1, x2, y2 = raw_bbox

        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            return DetectionResult(
                status="face_out_of_frame",
                message="Keep your entire face inside the camera view.",
                confidence=confidence
            )

        x1 = int(np.floor(x1))
        y1 = int(np.floor(y1))
        x2 = int(np.ceil(x2))
        y2 = int(np.ceil(y2))

        face_width = x2 - x1
        face_height = y2 - y1

        if face_width <= 0 or face_height <= 0:
            return DetectionResult(
                status="invalid_detection",
                message="Invalid face dimensions."
            )

        if (
            face_width < self.min_face_width
            or face_height < self.min_face_height
        ):
            return DetectionResult(
                status="face_too_small",
                message="Move closer to the camera.",
                bbox=(x1, y1, x2, y2),
                confidence=confidence
            )

        landmarks = np.asarray(face.kps, dtype=np.float32)

        if (
            landmarks.shape != (5, 2)
            or not np.all(np.isfinite(landmarks))
        ):
            return DetectionResult(
                status="invalid_landmarks",
                message="Facial landmarks could not be detected reliably.",
                bbox=(x1, y1, x2, y2),
                confidence=confidence
            )

        crop = frame[y1:y2, x1:x2].copy()

        if crop.size == 0:
            return DetectionResult(
                status="invalid_detection",
                message="Could not extract the face image.",
                confidence=confidence
            )

        return DetectionResult(
            status="valid",
            message="Face detected successfully.",
            face=face,
            bbox=(x1, y1, x2, y2),
            landmarks=landmarks.copy(),
            confidence=confidence,
            crop=crop
        )


face_detector = FaceDetector()
