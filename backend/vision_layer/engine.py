
import threading

import cv2
import numpy as np
from insightface.app import FaceAnalysis


class FaceEngine:
    def __init__(self):
        self.model_name = "buffalo_l"
        self.detection_size = (640, 640)
        self.detection_threshold = 0.5
        self.providers = ["CPUExecutionProvider"]

        self._app = None
        self._initialization_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    def initialize(self):
        if self._app is not None:
            return

        with self._initialization_lock:
            if self._app is not None:
                return

            try:
                app = FaceAnalysis(
                    name=self.model_name,
                    allowed_modules=["detection", "recognition"],
                    providers=self.providers
                )

                app.prepare(
                    ctx_id=-1,
                    det_size=self.detection_size,
                    det_thresh=self.detection_threshold
                )

                self._app = app

            except Exception as error:
                raise RuntimeError(
                    f"Failed to initialize face recognition model: {error}"
                ) from error

    def analyze(self, frame):
        if not isinstance(frame, np.ndarray):
            raise ValueError("Frame must be a NumPy array.")

        if frame.size == 0:
            raise ValueError("Frame cannot be empty.")

        if frame.dtype != np.uint8:
            raise ValueError("Frame must use uint8 image data.")

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Frame must be a three-channel BGR image.")

        self.initialize()

        with self._inference_lock:
            faces = self._app.get(frame)

        return faces

    @property
    def is_initialized(self):
        return self._app is not None


face_engine = FaceEngine()
