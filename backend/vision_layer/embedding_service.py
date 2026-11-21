
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class EmbeddingResult:
    status: str
    message: str

    embedding: Optional[np.ndarray] = None

    @property
    def is_valid(self):
        return self.status == "valid"


class EmbeddingService:

    def __init__(
        self,
        expected_dimension=512,
        model_name="buffalo_l"
    ):
        self.expected_dimension = expected_dimension
        self.model_name = model_name

    def generate(self, detection):

        if not detection.is_valid:
            return EmbeddingResult(
                status="invalid_detection",
                message="A valid face detection is required."
            )

        if detection.face is None:
            return EmbeddingResult(
                status="missing_face",
                message="Face recognition data is unavailable."
            )

        raw_embedding = getattr(
            detection.face,
            "normed_embedding",
            None
        )

        if raw_embedding is None:
            return EmbeddingResult(
                status="missing_embedding",
                message="Could not generate a face embedding."
            )

        embedding = np.asarray(
            raw_embedding,
            dtype=np.float32
        )

        if embedding.ndim != 1:
            return EmbeddingResult(
                status="invalid_embedding",
                message="Embedding must be a one-dimensional vector."
            )

        if embedding.shape[0] != self.expected_dimension:
            return EmbeddingResult(
                status="invalid_dimension",
                message="Unexpected face embedding dimensions."
            )

        if not np.all(np.isfinite(embedding)):
            return EmbeddingResult(
                status="invalid_embedding",
                message="Embedding contains invalid numerical values."
            )

        magnitude = float(np.linalg.norm(embedding))

        if not np.isfinite(magnitude) or magnitude <= 1e-8:
            return EmbeddingResult(
                status="invalid_embedding",
                message="Embedding has an invalid magnitude."
            )

        normalized_embedding = embedding / magnitude

        return EmbeddingResult(
            status="valid",
            message="Face embedding generated successfully.",
            embedding=normalized_embedding.astype(np.float32)
        )

    def serialize(self, embedding):

        if embedding is None:
            raise ValueError("Embedding cannot be empty.")

        embedding = np.asarray(
            embedding,
            dtype=np.float32
        )

        if (
            embedding.ndim != 1
            or embedding.shape[0] != self.expected_dimension
        ):
            raise ValueError("Invalid embedding dimensions.")

        if not np.all(np.isfinite(embedding)):
            raise ValueError("Embedding contains invalid values.")

        magnitude = float(np.linalg.norm(embedding))

        if magnitude <= 1e-8 or not np.isfinite(magnitude):
            raise ValueError("Invalid embedding magnitude.")

        normalized_embedding = embedding / magnitude

        return normalized_embedding.astype(
            np.float32
        ).tobytes()

    def deserialize(self, embedding_bytes):

        if not embedding_bytes:
            raise ValueError("Embedding data cannot be empty.")

        expected_bytes = self.expected_dimension * 4

        if len(embedding_bytes) != expected_bytes:
            raise ValueError("Invalid serialized embedding size.")

        embedding = np.frombuffer(
            embedding_bytes,
            dtype=np.float32
        ).copy()

        if not np.all(np.isfinite(embedding)):
            raise ValueError("Embedding contains invalid values.")

        magnitude = float(np.linalg.norm(embedding))

        if magnitude <= 1e-8 or not np.isfinite(magnitude):
            raise ValueError("Invalid embedding magnitude.")

        return embedding / magnitude


embedding_service = EmbeddingService()
