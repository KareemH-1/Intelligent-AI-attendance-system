
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from database import get_connection
from vision_layer.embedding_service import embedding_service


@dataclass
class IdentityVerificationResult:
    status: str
    message: str

    expected_person_similarity: Optional[float] = None
    expected_person_matching_poses: int = 0

    conflicting_person: Optional[dict] = None

    checked_people: int = 0
    threshold: float = 0.45

    @property
    def is_valid(self):
        return self.status == "clear"


class IdentityVerifier:

    REQUIRED_POSES = [
        "FRONT",
        "LEFT",
        "RIGHT",
        "UP",
        "DOWN"
    ]

    SIMILARITY_THRESHOLD = 0.45
    MIN_MATCHING_POSES = 3
    EXPECTED_DIMENSION = 512

    def __init__(self):
        self.model_name = embedding_service.model_name

    def _normalize_embedding(self, embedding):

        vector = np.asarray(
            embedding,
            dtype=np.float32
        )

        if vector.ndim != 1:
            raise ValueError("Embedding must be one-dimensional.")

        if vector.size != self.EXPECTED_DIMENSION:
            raise ValueError("Embedding must contain 512 values.")

        if not np.all(np.isfinite(vector)):
            raise ValueError("Embedding contains invalid values.")

        magnitude = float(np.linalg.norm(vector))

        if magnitude <= 1e-8:
            raise ValueError("Embedding has an invalid magnitude.")

        return vector / magnitude

    def _calculate_similarity(
        self,
        first_embedding,
        second_embedding
    ):

        similarity = float(
            np.dot(first_embedding, second_embedding)
        )

        return float(
            np.clip(similarity, -1.0, 1.0)
        )

    def _calculate_person_score(
        self,
        new_embeddings,
        stored_embeddings
    ):

        pose_similarities = {}

        stored_by_pose = {}

        for stored in stored_embeddings:

            pose_name = stored["pose_label"]

            if pose_name:
                if pose_name not in stored_by_pose:
                    stored_by_pose[pose_name] = []

                stored_by_pose[pose_name].append(
                    stored["embedding"]
                )

        all_stored_embeddings = [
            stored["embedding"]
            for stored in stored_embeddings
        ]

        for pose_name in self.REQUIRED_POSES:

            candidates = stored_by_pose.get(pose_name)

            if not candidates:
                candidates = all_stored_embeddings

            if not candidates:
                continue

            similarities = []

            for stored_embedding in candidates:

                similarity = self._calculate_similarity(
                    new_embeddings[pose_name],
                    stored_embedding
                )

                similarities.append(similarity)

            pose_similarities[pose_name] = max(similarities)

        if not pose_similarities:
            return None

        matching_poses = 0

        for similarity in pose_similarities.values():

            if similarity >= self.SIMILARITY_THRESHOLD:
                matching_poses += 1

        average_similarity = float(
            np.mean(list(pose_similarities.values()))
        )

        return {
            "average_similarity": average_similarity,
            "matching_poses": matching_poses,
            "pose_similarities": pose_similarities
        }

    def verify_identity(
        self,
        person_id,
        samples
    ):

        if not isinstance(samples, dict):
            return IdentityVerificationResult(
                status="invalid",
                message="Registration samples must be a dictionary.",
                threshold=self.SIMILARITY_THRESHOLD
            )

        normalized_samples = {}

        try:

            for pose_name in self.REQUIRED_POSES:

                if pose_name not in samples:
                    raise ValueError(
                        f"Missing {pose_name} embedding."
                    )

                normalized_samples[pose_name] = (
                    self._normalize_embedding(
                        samples[pose_name]
                    )
                )

        except ValueError as error:

            return IdentityVerificationResult(
                status="invalid",
                message=str(error),
                threshold=self.SIMILARITY_THRESHOLD
            )

        connection = None
        cursor = None

        try:

            connection = get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    fe.person_id,
                    fe.embedding,
                    fe.embedding_dimension,
                    fe.model_name,
                    fe.pose_label,
                    p.university_id,
                    p.full_name
                FROM FaceEmbeddings fe
                INNER JOIN People p
                    ON p.person_id = fe.person_id
                WHERE
                    fe.is_active = 1
                    AND fe.model_name = ?
                    AND fe.embedding_dimension = ?
                """,
                self.model_name,
                self.EXPECTED_DIMENSION
            )

            rows = cursor.fetchall()

            people_embeddings = {}

            for row in rows:

                stored_person_id = int(row[0])

                if stored_person_id not in people_embeddings:
                    people_embeddings[stored_person_id] = {
                        "university_id": row[5],
                        "full_name": row[6],
                        "embeddings": []
                    }

                stored_embedding = embedding_service.deserialize(
                    row[1]
                )

                normalized_embedding = (
                    self._normalize_embedding(stored_embedding)
                )

                people_embeddings[stored_person_id]["embeddings"].append({
                    "embedding": normalized_embedding,
                    "pose_label": row[4]
                })

            expected_person = people_embeddings.get(
                person_id
            )

            expected_similarity = None
            expected_matching_poses = 0

            if expected_person:

                expected_score = self._calculate_person_score(
                    normalized_samples,
                    expected_person["embeddings"]
                )

                if expected_score:
                    expected_similarity = (
                        expected_score["average_similarity"]
                    )

                    expected_matching_poses = (
                        expected_score["matching_poses"]
                    )

            conflicting_person = None

            checked_people = 0

            for stored_person_id, person_data in people_embeddings.items():

                if stored_person_id == person_id:
                    continue

                checked_people += 1

                score = self._calculate_person_score(
                    normalized_samples,
                    person_data["embeddings"]
                )

                if not score:
                    continue

                is_match = (
                    score["average_similarity"] >=
                    self.SIMILARITY_THRESHOLD
                    and
                    score["matching_poses"] >=
                    self.MIN_MATCHING_POSES
                )

                if is_match:

                    if (
                        conflicting_person is None
                        or score["average_similarity"] >
                        conflicting_person["similarity"]
                    ):

                        conflicting_person = {
                            "person_id": stored_person_id,
                            "university_id": person_data["university_id"],
                            "full_name": person_data["full_name"],
                            "similarity": score["average_similarity"],
                            "matching_poses": score["matching_poses"],
                            "pose_similarities": score["pose_similarities"]
                        }

            if conflicting_person:

                return IdentityVerificationResult(
                    status="duplicate_identity",
                    message=(
                        "The captured face appears to match another "
                        "registered person."
                    ),
                    expected_person_similarity=expected_similarity,
                    expected_person_matching_poses=expected_matching_poses,
                    conflicting_person=conflicting_person,
                    checked_people=checked_people,
                    threshold=self.SIMILARITY_THRESHOLD
                )

            if expected_person:

                expected_match = (
                    expected_similarity is not None
                    and expected_similarity >= self.SIMILARITY_THRESHOLD
                    and expected_matching_poses >= self.MIN_MATCHING_POSES
                )

                if not expected_match:

                    return IdentityVerificationResult(
                        status="identity_mismatch",
                        message=(
                            "The captured face could not be verified "
                            "against this student's existing registration."
                        ),
                        expected_person_similarity=expected_similarity,
                        expected_person_matching_poses=expected_matching_poses,
                        checked_people=checked_people,
                        threshold=self.SIMILARITY_THRESHOLD
                    )

            return IdentityVerificationResult(
                status="clear",
                message=(
                    "No conflicting registered identity was detected."
                ),
                expected_person_similarity=expected_similarity,
                expected_person_matching_poses=expected_matching_poses,
                checked_people=checked_people,
                threshold=self.SIMILARITY_THRESHOLD
            )

        except Exception as error:

            return IdentityVerificationResult(
                status="error",
                message=f"Identity verification failed: {str(error)}",
                threshold=self.SIMILARITY_THRESHOLD
            )

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()


identity_verifier = IdentityVerifier()
