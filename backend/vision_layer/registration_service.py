
from dataclasses import dataclass
from typing import Optional

import numpy as np

from vision_layer.face_detector import face_detector
from vision_layer.pose_estimator import pose_estimator
from vision_layer.quality_validator import quality_validator
from vision_layer.embedding_service import embedding_service


@dataclass
class RegistrationFrameResult:
    status: str
    message: str

    pose_name: Optional[str] = None
    yaw: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None

    brightness: Optional[float] = None
    sharpness: Optional[float] = None

    embedding: Optional[np.ndarray] = None
    bbox: Optional[tuple] = None
    
    @property
    def is_valid(self):
        return self.status == "valid"


class RegistrationService:

    SUPPORTED_POSES = [
        "FRONT",
        "LEFT",
        "RIGHT",
        "UP",
        "DOWN"
    ]

    def evaluate_frame(self, frame, expected_pose):

        if expected_pose is None:
            return RegistrationFrameResult(
                status="invalid_pose",
                message="An expected face position is required."
            )

        expected_pose = expected_pose.upper()

        if expected_pose not in self.SUPPORTED_POSES:
            return RegistrationFrameResult(
                status="invalid_pose",
                message="Unsupported face position."
            )

        detection = face_detector.detect(frame)

        if not detection.is_valid:
            return RegistrationFrameResult(
                status=detection.status,
                message=detection.message,
                bbox=detection.bbox,
                pose_name=expected_pose
            )

        quality = quality_validator.validate(
            detection,
            frame
        )

        if not quality.is_valid:
            return RegistrationFrameResult(
                status=quality.status,
                message=quality.message,
                pose_name=expected_pose,
                brightness=quality.brightness,
                sharpness=quality.sharpness,
                bbox=detection.bbox
            )

        pose = pose_estimator.estimate(
            detection,
            frame
        )

        if not pose.is_valid:
            return RegistrationFrameResult(
                status=pose.status,
                message=pose.message,
                pose_name=expected_pose,
                brightness=quality.brightness,
                sharpness=quality.sharpness,
                bbox=detection.bbox
                
            )

        if not pose_estimator.matches_pose(
            expected_pose,
            pose
        ):
            return RegistrationFrameResult(
                status="wrong_pose",
                message=pose_estimator.get_pose_feedback(
                    expected_pose,
                    pose
                ),
                pose_name=expected_pose,
                yaw=pose.yaw,
                pitch=pose.pitch,
                roll=pose.roll,
                brightness=quality.brightness,
                sharpness=quality.sharpness,
                bbox=detection.bbox
                
            )

        embedding_result = embedding_service.generate(
            detection
        )

        if not embedding_result.is_valid:
            return RegistrationFrameResult(
                status=embedding_result.status,
                message=embedding_result.message,
                pose_name=expected_pose,
                yaw=pose.yaw,
                pitch=pose.pitch,
                roll=pose.roll,
                brightness=quality.brightness,
                sharpness=quality.sharpness
            )

        return RegistrationFrameResult(
            status="valid",
            message="Face position and image quality are acceptable.",
            pose_name=expected_pose,
            yaw=pose.yaw,
            pitch=pose.pitch,
            roll=pose.roll,
            brightness=quality.brightness,
            sharpness=quality.sharpness,
            embedding=embedding_result.embedding,
            bbox=detection.bbox
        )

    def get_pose_instruction(self, pose_name):

        instructions = {
            "FRONT": "Look directly at the camera.",
            "LEFT": "Turn your head slightly to your left.",
            "RIGHT": "Turn your head slightly to your right.",
            "UP": "Tilt your head slightly upward.",
            "DOWN": "Tilt your head slightly downward."
        }

        return instructions[pose_name]


registration_service = RegistrationService()
