
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class VerificationResult:
    status: str
    message: str

    similarity: Optional[float] = None
    threshold: Optional[float] = None

    @property
    def is_match(self):
        return self.status == "matched"


class FaceVerification:

    def __init__(self, similarity_threshold=0.45):
        self.similarity_threshold = similarity_threshold

    def _prepare_embedding(self, embedding):

        if embedding is None:
            raise ValueError("Embedding cannot be empty.")

        vector = np.asarray(
            embedding,
            dtype=np.float32
        )

        if vector.ndim != 1 or vector.shape[0] != 512:
            raise ValueError("Embedding must contain 512 dimensions.")

        if not np.all(np.isfinite(vector)):
            raise ValueError("Embedding contains invalid values.")

        magnitude = float(np.linalg.norm(vector))

        if not np.isfinite(magnitude) or magnitude <= 1e-8:
            raise ValueError("Embedding has an invalid magnitude.")

        return vector / magnitude

    def calculate_similarity(
        self,
        reference_embedding,
        candidate_embedding
    ):

        reference = self._prepare_embedding(
            reference_embedding
        )

        candidate = self._prepare_embedding(
            candidate_embedding
        )

        similarity = float(
            np.dot(reference, candidate)
        )

        return float(
            np.clip(similarity, -1.0, 1.0)
        )

    def verify(
        self,
        reference_embedding,
        candidate_embedding
    ):

        try:

            similarity = self.calculate_similarity(
                reference_embedding,
                candidate_embedding
            )

            if similarity >= self.similarity_threshold:
                return VerificationResult(
                    status="matched",
                    message="Face identity verified.",
                    similarity=similarity,
                    threshold=self.similarity_threshold
                )

            return VerificationResult(
                status="not_matched",
                message="Face identity could not be verified.",
                similarity=similarity,
                threshold=self.similarity_threshold
            )

        except ValueError as error:

            return VerificationResult(
                status="invalid_embedding",
                message=str(error),
                threshold=self.similarity_threshold
            )


face_verification = FaceVerification()
