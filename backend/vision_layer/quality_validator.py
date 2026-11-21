
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class QualityResult:
    status: str
    message: str

    brightness: Optional[float] = None
    sharpness: Optional[float] = None
    face_width: Optional[int] = None
    face_height: Optional[int] = None

    @property
    def is_valid(self):
        return self.status == "valid"


class QualityValidator:

    def __init__(
        self,
        min_brightness=35.0,
        max_brightness=225.0,
        min_sharpness=15.0,
        min_face_width=100,
        min_face_height=100,
        min_face_margin=0.02
    ):
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_sharpness = min_sharpness

        self.min_face_width = min_face_width
        self.min_face_height = min_face_height

        self.min_face_margin = min_face_margin

    def validate(self, detection, frame):

        if not detection.is_valid:
            return QualityResult(
                status="invalid_detection",
                message="A valid face detection is required."
            )

        if (
            frame is None
            or not isinstance(frame, np.ndarray)
            or frame.size == 0
            or frame.ndim != 3
            or frame.shape[2] != 3
        ):
            return QualityResult(
                status="invalid_frame",
                message="Invalid camera frame."
            )

        if detection.crop is None or detection.crop.size == 0:
            return QualityResult(
                status="invalid_crop",
                message="Could not evaluate the detected face."
            )

        height, width = frame.shape[:2]

        x1, y1, x2, y2 = detection.bbox

        face_width = x2 - x1
        face_height = y2 - y1

        if face_width <= 0 or face_height <= 0:
            return QualityResult(
                status="invalid_crop",
                message="Invalid face dimensions."
            )

        if (
            face_width < self.min_face_width
            or face_height < self.min_face_height
        ):
            return QualityResult(
                status="face_too_small",
                message="Move slightly closer to the camera.",
                face_width=face_width,
                face_height=face_height
            )

        margin_x = face_width * self.min_face_margin
        margin_y = face_height * self.min_face_margin

        if (
            x1 < margin_x
            or y1 < margin_y
            or x2 > width - margin_x
            or y2 > height - margin_y
        ):
            return QualityResult(
                status="face_too_close_to_edge",
                message="Move your face towards the center.",
                face_width=face_width,
                face_height=face_height
            )

        gray = cv2.cvtColor(
            detection.crop,
            cv2.COLOR_BGR2GRAY
        )

        brightness = float(np.mean(gray))

        if not np.isfinite(brightness):
            return QualityResult(
                status="invalid_image",
                message="Could not evaluate image brightness."
            )

        if brightness < self.min_brightness:
            return QualityResult(
                status="too_dark",
                message="Lighting is too low. Move to a brighter area.",
                brightness=brightness,
                face_width=face_width,
                face_height=face_height
            )

        if brightness > self.max_brightness:
            return QualityResult(
                status="too_bright",
                message="Lighting is too strong. Avoid direct bright light.",
                brightness=brightness,
                face_width=face_width,
                face_height=face_height
            )

        laplacian = cv2.Laplacian(
            gray,
            cv2.CV_64F
        )

        sharpness = float(laplacian.var())

        if not np.isfinite(sharpness):
            return QualityResult(
                status="invalid_image",
                message="Could not evaluate image sharpness."
            )

        if sharpness < self.min_sharpness:
            return QualityResult(
                status="blurry",
                message="Image is too blurry. Hold the camera steady.",
                brightness=brightness,
                sharpness=sharpness,
                face_width=face_width,
                face_height=face_height
            )

        return QualityResult(
            status="valid",
            message="Image quality is acceptable.",
            brightness=brightness,
            sharpness=sharpness,
            face_width=face_width,
            face_height=face_height
        )


quality_validator = QualityValidator()
