
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict

import numpy as np


@dataclass
class RegistrationVerificationResult:
    status: str
    message: str
    similarities: Dict[str, float] = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def is_valid(self):
        return self.status == "valid"


class RegistrationVerifier:
    REQUIRED_POSES = [
        "FRONT",
        "LEFT",
        "RIGHT",
        "UP",
        "DOWN"
    ]

    EXPECTED_DIMENSION = 512

    def verify_samples(self, samples):
        if not isinstance(samples, dict):
            return RegistrationVerificationResult(
                status="invalid",
                message="Registration samples must be a dictionary."
            )

        missing_poses = []

        for pose_name in self.REQUIRED_POSES:
            if pose_name not in samples:
                missing_poses.append(pose_name)

        if missing_poses:
            return RegistrationVerificationResult(
                status="invalid",
                message=f"Missing poses: {', '.join(missing_poses)}"
            )

        normalized_embeddings = {}

        for pose_name in self.REQUIRED_POSES:
            embedding = np.asarray(
                samples[pose_name],
                dtype=np.float32
            )

            if embedding.ndim != 1:
                return RegistrationVerificationResult(
                    status="invalid",
                    message=f"{pose_name} embedding must be one-dimensional."
                )

            if embedding.size != self.EXPECTED_DIMENSION:
                return RegistrationVerificationResult(
                    status="invalid",
                    message=f"{pose_name} embedding must contain 512 values."
                )

            if not np.all(np.isfinite(embedding)):
                return RegistrationVerificationResult(
                    status="invalid",
                    message=f"{pose_name} embedding contains invalid values."
                )

            norm = np.linalg.norm(embedding)

            if norm < 1e-8:
                return RegistrationVerificationResult(
                    status="invalid",
                    message=f"{pose_name} embedding has zero magnitude."
                )

            normalized_embeddings[pose_name] = embedding / norm

        similarities = {}

        for pose_a, pose_b in combinations(
            self.REQUIRED_POSES,
            2
        ):
            similarity = float(
                np.dot(
                    normalized_embeddings[pose_a],
                    normalized_embeddings[pose_b]
                )
            )

            similarity = float(np.clip(similarity, -1.0, 1.0))

            pair_name = f"{pose_a} - {pose_b}"
            similarities[pair_name] = similarity

        return RegistrationVerificationResult(
            status="valid",
            message="All five embeddings passed structural validation.",
            similarities=similarities
        )


registration_verifier = RegistrationVerifier()
