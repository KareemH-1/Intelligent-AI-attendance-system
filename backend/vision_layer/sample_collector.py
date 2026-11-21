
from dataclasses import dataclass, field
from typing import Dict, Optional
import time

import cv2
import numpy as np


@dataclass
class CaptureResult:
    status: str
    message: str
    pose_name: Optional[str] = None
    progress: int = 0
    embedding: Optional[np.ndarray] = None

    @property
    def is_captured(self):
        return self.status == "captured"


@dataclass
class RegistrationSamples:
    embeddings: Dict[str, np.ndarray] = field(default_factory=dict)
    images: Dict[str, bytes] = field(default_factory=dict)
    bounding_boxes: Dict[str, tuple] = field(default_factory=dict)


class SampleCollector:
    REQUIRED_POSES = ["FRONT", "LEFT", "RIGHT", "UP", "DOWN"]

    def __init__(
        self,
        required_frames=8,
        stability_duration=0.8,
        max_frame_gap=2
    ):
        self.required_frames = required_frames
        self.stability_duration = stability_duration
        self.max_frame_gap = max_frame_gap

        self.samples = RegistrationSamples()
        self.current_pose = None
        self.frame_embeddings = []

        self.reset_stability()

    def start_pose(self, pose_name):
        pose_name = pose_name.upper()

        if pose_name not in self.REQUIRED_POSES:
            raise ValueError(f"Unsupported pose: {pose_name}")

        self.current_pose = pose_name
        self.reset_stability()

    def reset_stability(self):
        self.frame_embeddings = []
        self.first_valid_time = None
        self.last_valid_time = None

    def update(self, frame_result, frame):
        if self.current_pose is None:
            return CaptureResult(
                status="not_started",
                message="Start a pose before collecting samples."
            )

        if self.current_pose in self.samples.embeddings:
            return CaptureResult(
                status="already_captured",
                message=f"{self.current_pose} has already been captured.",
                pose_name=self.current_pose
            )

        if not frame_result.is_valid:
            self.reset_stability()

            return CaptureResult(
                status="invalid_frame",
                message=frame_result.message,
                pose_name=self.current_pose
            )

        if frame_result.embedding is None:
            self.reset_stability()

            return CaptureResult(
                status="invalid_embedding",
                message="No face embedding was generated.",
                pose_name=self.current_pose
            )

        if frame_result.bbox is None:
            self.reset_stability()

            return CaptureResult(
                status="invalid_detection",
                message="The face bounding box is missing.",
                pose_name=self.current_pose
            )

        if frame is None or frame.size == 0:
            self.reset_stability()

            return CaptureResult(
                status="invalid_frame",
                message="The captured image is empty.",
                pose_name=self.current_pose
            )

        embedding = np.asarray(
            frame_result.embedding,
            dtype=np.float32
        )

        if (
            embedding.ndim != 1
            or embedding.size != 512
            or not np.all(np.isfinite(embedding))
        ):
            self.reset_stability()

            return CaptureResult(
                status="invalid_embedding",
                message="The face embedding is invalid.",
                pose_name=self.current_pose
            )

        norm = np.linalg.norm(embedding)

        if norm < 1e-8:
            self.reset_stability()

            return CaptureResult(
                status="invalid_embedding",
                message="The face embedding has zero magnitude.",
                pose_name=self.current_pose
            )

        embedding = embedding / norm

        now = time.monotonic()

        if (
            self.last_valid_time is not None
            and now - self.last_valid_time > self.max_frame_gap
        ):
            self.reset_stability()

        if self.first_valid_time is None:
            self.first_valid_time = now

        self.frame_embeddings.append(embedding.copy())
        self.last_valid_time = now

        elapsed = now - self.first_valid_time

        frame_progress = min(
            100,
            int(
                len(self.frame_embeddings)
                / self.required_frames * 100
            )
        )

        time_progress = min(
            100,
            int(elapsed / self.stability_duration * 100)
        )

        progress = min(frame_progress, time_progress)

        if (
            len(self.frame_embeddings) >= self.required_frames
            and elapsed >= self.stability_duration
        ):
            average_embedding = np.mean(
                np.array(self.frame_embeddings),
                axis=0
            )

            average_norm = np.linalg.norm(average_embedding)

            if average_norm < 1e-8:
                self.reset_stability()

                return CaptureResult(
                    status="invalid_embedding",
                    message="Could not produce a stable face embedding.",
                    pose_name=self.current_pose
                )

            final_embedding = (
                average_embedding / average_norm
            ).astype(np.float32)

            success, encoded_image = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 90]
            )

            if not success:
                self.reset_stability()

                return CaptureResult(
                    status="image_encoding_failed",
                    message="Could not save the captured face image.",
                    pose_name=self.current_pose
                )

            captured_pose = self.current_pose

            self.samples.embeddings[captured_pose] = (
                final_embedding.copy()
            )

            self.samples.images[captured_pose] = (
                encoded_image.tobytes()
            )

            self.samples.bounding_boxes[captured_pose] = tuple(
                int(value) for value in frame_result.bbox
            )

            self.reset_stability()

            return CaptureResult(
                status="captured",
                message=f"{captured_pose} pose captured successfully.",
                pose_name=captured_pose,
                progress=100,
                embedding=final_embedding
            )

        return CaptureResult(
            status="stabilizing",
            message="Hold your position.",
            pose_name=self.current_pose,
            progress=progress
        )

    def retake(self, pose_name):
        pose_name = pose_name.upper()

        if pose_name not in self.REQUIRED_POSES:
            raise ValueError(f"Unsupported pose: {pose_name}")

        self.samples.embeddings.pop(pose_name, None)
        self.samples.images.pop(pose_name, None)
        self.samples.bounding_boxes.pop(pose_name, None)

        self.start_pose(pose_name)

    def is_complete(self):
        for pose_name in self.REQUIRED_POSES:
            if (
                pose_name not in self.samples.embeddings
                or pose_name not in self.samples.images
                or pose_name not in self.samples.bounding_boxes
            ):
                return False

        return True

    def get_samples(self):
        if not self.is_complete():
            raise ValueError(
                "All five poses must be captured before retrieving samples."
            )

        return {
            pose_name: embedding.copy()
            for pose_name, embedding in self.samples.embeddings.items()
        }

    def get_captured_photos(self):
        if not self.is_complete():
            raise ValueError(
                "All five poses must be captured before retrieving photos."
            )

        return {
            pose_name: {
                "image": self.samples.images[pose_name],
                "bbox": self.samples.bounding_boxes[pose_name]
            }
            for pose_name in self.REQUIRED_POSES
        }

    def reset(self):
        self.samples = RegistrationSamples()
        self.current_pose = None
        self.reset_stability()


sample_collector = SampleCollector()
