
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class PoseResult:
    status: str
    message: str

    yaw: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None
    reprojection_error: Optional[float] = None

    @property
    def is_valid(self):
        return self.status == "valid"


class PoseEstimator:

    FACE_MODEL_POINTS = np.array(
        [
            [-30.0,  -30.0, 30.0],
            [ 30.0,  -30.0, 30.0],
            [  0.0,   0.0, 60.0],
            [-25.0, 30.0, 25.0],
            [ 25.0, 30.0, 25.0]
        ],
        dtype=np.float64
    )

    POSE_RANGES = {
    "FRONT": {
        "yaw": (-10.0, 10.0),
        "pitch": (-15.0, 10.0),
        "roll": (-15.0, 15.0)
    },
    "LEFT": {
        "yaw": (11.0, 35.0),
        "pitch": (-15.0, 15.0),
        "roll": (-15.0, 15.0)
    },
    "RIGHT": {
        "yaw": (-35.0, -11.0),
        "pitch": (-15.0, 15.0),
        "roll": (-15.0, 15.0)
    },
    "UP": {
        "yaw": (-12.0, 12.0),
        "pitch": (10.0, 25.0),
        "roll": (-15.0, 15.0)
    },
    "DOWN": {
        "yaw": (-12.0, 12.0),
        "pitch": (-25.0, -15.0),
        "roll": (-15.0, 15.0)
    }
    }

    def estimate(self, detection, frame):

        if not detection.is_valid:
            return PoseResult(
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
            return PoseResult(
                status="invalid_frame",
                message="Invalid camera frame."
            )

        image_points = np.asarray(
            detection.landmarks,
            dtype=np.float64
        )

        if (
            image_points.shape != (5, 2)
            or not np.all(np.isfinite(image_points))
        ):
            return PoseResult(
                status="invalid_landmarks",
                message="Facial landmarks are invalid."
            )

        height, width = frame.shape[:2]

        focal_length = float(max(width, height))

        camera_matrix = np.array(
            [
                [focal_length, 0.0, width / 2.0],
                [0.0, focal_length, height / 2.0],
                [0.0, 0.0, 1.0]
            ],
            dtype=np.float64
        )

        distortion_coefficients = np.zeros(
            (4, 1),
            dtype=np.float64
        )

        try:

            success, rotation_vector, translation_vector = (
                cv2.solvePnP(
                    self.FACE_MODEL_POINTS,
                    image_points,
                    camera_matrix,
                    distortion_coefficients,
                    flags=cv2.SOLVEPNP_SQPNP
                )
            )

            if not success:
                return PoseResult(
                    status="pose_estimation_failed",
                    message="Could not estimate head orientation."
                )

            if translation_vector[2, 0] <= 0:
                return PoseResult(
                    status="pose_estimation_failed",
                    message="Invalid face position relative to camera."
                )

            rotation_vector, translation_vector = (
                cv2.solvePnPRefineLM(
                    self.FACE_MODEL_POINTS,
                    image_points,
                    camera_matrix,
                    distortion_coefficients,
                    rotation_vector,
                    translation_vector
                )
            )

            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

            angles = cv2.RQDecomp3x3(rotation_matrix)[0]

            pitch = float(angles[0])
            yaw = float(angles[1])
            roll = float(angles[2])

            if not np.all(
                np.isfinite([yaw, pitch, roll])
            ):
                return PoseResult(
                    status="pose_estimation_failed",
                    message="Invalid head orientation."
                )

            projected_points, _ = cv2.projectPoints(
                self.FACE_MODEL_POINTS,
                rotation_vector,
                translation_vector,
                camera_matrix,
                distortion_coefficients
            )

            projected_points = projected_points.reshape(-1, 2)

            errors = np.linalg.norm(
                image_points - projected_points,
                axis=1
            )

            reprojection_error = float(
                np.sqrt(np.mean(errors ** 2))
            )

            if not np.isfinite(reprojection_error):
                return PoseResult(
                    status="pose_estimation_failed",
                    message="Invalid pose estimation quality."
                )

            return PoseResult(
                status="valid",
                message="Head orientation estimated successfully.",
                yaw=yaw,
                pitch=pitch,
                roll=roll,
                reprojection_error=reprojection_error
            )

        except cv2.error as error:

            print("OpenCV Pose Estimation Error:", error)

            return PoseResult(
                status="pose_estimation_failed",
                message="Head orientation estimation failed."
            )

    def matches_pose(self, pose_name, pose_result):

        if not pose_result.is_valid:
            return False

        ranges = self.POSE_RANGES.get(
            pose_name.upper()
        )

        if ranges is None:
            raise ValueError(
                f"Unsupported pose: {pose_name}"
            )

        return (
            ranges["yaw"][0] <= pose_result.yaw <= ranges["yaw"][1]
            and ranges["pitch"][0] <= pose_result.pitch <= ranges["pitch"][1]
            and ranges["roll"][0] <= pose_result.roll <= ranges["roll"][1]
        )


    def get_pose_feedback(self, pose_name, pose_result):
        if not pose_result.is_valid:
            return "Keep your face visible and look toward the camera."

        pose_name = pose_name.upper()
        ranges = self.POSE_RANGES.get(pose_name)

        if ranges is None:
            raise ValueError(f"Unsupported pose: {pose_name}")

        yaw = pose_result.yaw
        pitch = pose_result.pitch
        roll = pose_result.roll

        yaw_min, yaw_max = ranges["yaw"]
        pitch_min, pitch_max = ranges["pitch"]
        roll_min, roll_max = ranges["roll"]

        # Check horizontal head rotation first.
        if yaw < yaw_min:
            if pose_name == "LEFT":
                return "Turn your head a little further to your left."
            if pose_name == "RIGHT":
                return "Turn your head a little further to your right."
            return "Turn your head slightly toward the center."

        if yaw > yaw_max:
            if pose_name == "LEFT":
                return "You turned too far left. Bring your face slightly back toward the center."
            if pose_name == "RIGHT":
                return "You turned too far right. Bring your face slightly back toward the center."
            return "Keep your head facing forward. Avoid turning sideways."

        # Check vertical head rotation.
        if pitch < pitch_min:
            if pose_name == "UP":
                return "Look a little higher. Raise your chin slightly."
            if pose_name == "DOWN":
                return "Look a little lower. Lower your chin slightly."
            return "Your head is tilted too far downward. Raise your chin slightly."

        if pitch > pitch_max:
            if pose_name == "UP":
                return "You are looking too high. Lower your chin slightly."
            if pose_name == "DOWN":
                return "You are looking too low. Raise your chin slightly."
            return "Your head is tilted too far upward. Lower your chin slightly."

        # Check sideways head tilt.
        if roll < roll_min or roll > roll_max:
            return "Keep your head upright. Avoid tilting your ear toward your shoulder."

        return "Good position. Hold still while we capture your face."

pose_estimator = PoseEstimator()
