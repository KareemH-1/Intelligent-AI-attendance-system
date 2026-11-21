
import cv2
import numpy as np

from fastapi import APIRouter, HTTPException, UploadFile, File

from vision_layer.registration_session import registration_session_manager
from vision_layer.registration_service import registration_service
from vision_layer.registration_verifier import registration_verifier

import base64
from uuid import uuid4

from pydantic import BaseModel

from database import get_connection
from vision_layer.embedding_service import embedding_service

router = APIRouter(
    prefix="/registration",
    tags=["Face Registration"]
)


POSE_ORDER = ["FRONT", "LEFT", "RIGHT", "UP", "DOWN"]
MAX_IMAGE_SIZE = 8 * 1024 * 1024

class RegistrationSaveRequest(BaseModel):
    person_id: int
    
def get_registration_progress(collector):
    captured_poses = [
        pose for pose in POSE_ORDER
        if pose in collector.samples.embeddings
    ]

    missing_poses = [
        pose for pose in POSE_ORDER
        if pose not in collector.samples.embeddings
    ]

    return {
        "captured_poses": captured_poses,
        "missing_poses": missing_poses,
        "captured_count": len(captured_poses),
        "required_count": len(POSE_ORDER),
        "is_complete": collector.is_complete()
    }

def get_next_pose(collector):
    for pose in POSE_ORDER:
        if pose not in collector.samples.embeddings:
            return pose

    return None

def get_captured_photos(collector):
    photos = collector.get_captured_photos()

    captured_photos = []

    for pose in POSE_ORDER:
        photo = photos[pose]

        image_base64 = base64.b64encode(
            photo["image"]
        ).decode("utf-8")

        captured_photos.append({
            "pose_name": pose,
            "image": f"data:image/jpeg;base64,{image_base64}",
            "bbox": list(photo["bbox"])
        })

    return captured_photos


@router.post("/sessions")
def create_registration_session():
    try:
        session = registration_session_manager.create_session()

        session.collector.start_pose("FRONT")

        return {
            "session_id": session.session_id,
            "status": "created",
            "current_pose": "FRONT",
            "instruction": registration_service.get_pose_instruction("FRONT"),
            "progress": get_registration_progress(session.collector)
        }

    except RuntimeError as error:
        raise HTTPException(
            status_code=429,
            detail=str(error)
        )


@router.get("/sessions/{session_id}")
def get_registration_session(session_id: str):
    session = registration_session_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Registration session not found or expired."
        )

    with session.lock:
        collector = session.collector

        current_pose = collector.current_pose

        response = {
            "session_id": session.session_id,
            "status": "completed" if collector.is_complete() else "active",
            "current_pose": current_pose,
            "instruction": (
                registration_service.get_pose_instruction(current_pose)
                if current_pose else None
            ),
            "progress": get_registration_progress(collector)
        }

        if collector.is_complete():
            samples = collector.get_samples()
            response["captured_photos"] = get_captured_photos(collector)
                
            if samples is not None:
                sample_data = (
                    samples.embeddings
                    if hasattr(samples, "embeddings")
                    else samples
                )

                verification = registration_verifier.verify_samples(
                    sample_data
                )

                response["verification"] = {
                    "status": verification.status,
                    "message": verification.message,
                    "similarities": verification.similarities,
                    "warnings": verification.warnings
                }

        return response


@router.post("/sessions/{session_id}/capture")
async def capture_registration_frame(
    session_id: str,
    file: UploadFile = File(...)
):
    session = registration_session_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Registration session not found or expired."
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty."
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the maximum allowed size of 8 MB."
        )

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if frame is None:
        raise HTTPException(
            status_code=400,
            detail="Could not decode the uploaded image."
        )

    with session.lock:
        collector = session.collector

        if collector.is_complete():
            raise HTTPException(
                status_code=409,
                detail="Registration is already complete."
            )

        current_pose = collector.current_pose

        if current_pose is None:
            raise HTTPException(
                status_code=409,
                detail="No registration pose is currently active."
            )

        frame_result = registration_service.evaluate_frame(
            frame,
            current_pose
        )

        capture_result = collector.update(frame_result, frame)
        
        response = {
            "status": capture_result.status,
            "message": capture_result.message,
            "pose": current_pose,
            "progress": capture_result.progress,
            "registration_progress": get_registration_progress(collector)
        }

        if capture_result.is_captured:
            next_pose = get_next_pose(collector)

            if next_pose is not None:
                collector.start_pose(next_pose)

                response["next_pose"] = next_pose
                response["next_instruction"] = (
                    registration_service.get_pose_instruction(next_pose)
                )
            else:
                response["next_pose"] = None
                response["next_instruction"] = None

                samples = collector.get_samples()
                response["captured_photos"] = get_captured_photos(collector)
                sample_data = (
                    samples.embeddings
                    if hasattr(samples, "embeddings")
                    else samples
                )

                verification = registration_verifier.verify_samples(
                    sample_data
                )

                response["verification"] = {
                    "status": verification.status,
                    "message": verification.message,
                    "similarities": verification.similarities,
                    "warnings": verification.warnings
                }

        return response


@router.post("/sessions/{session_id}/retake/{pose_name}")
def retake_registration_pose(
    session_id: str,
    pose_name: str
):
    session = registration_session_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Registration session not found or expired."
        )

    pose_name = pose_name.upper()

    if pose_name not in POSE_ORDER:
        raise HTTPException(
            status_code=400,
            detail="Unsupported pose."
        )

    with session.lock:
        collector = session.collector

        collector.retake(pose_name)

        return {
            "status": "retake_started",
            "pose": pose_name,
            "instruction": registration_service.get_pose_instruction(
                pose_name
            ),
            "progress": get_registration_progress(collector)
        }


@router.post("/sessions/{session_id}/save")
def save_registration(
    session_id: str,
    request: RegistrationSaveRequest
):
    session = registration_session_manager.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Registration session not found or expired."
        )

    with session.lock:
        collector = session.collector

        if not collector.is_complete():
            raise HTTPException(
                status_code=409,
                detail="All five face poses must be captured before saving."
            )

        samples = collector.get_samples()

        sample_data = samples

        verification = registration_verifier.verify_samples(
            sample_data
        )

        if verification.status != "valid":
            raise HTTPException(
                status_code=400,
                detail=verification.message
            )

        registration_id = str(uuid4())

        connection = None

        try:
            connection = get_connection()
            connection.autocommit = False

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT person_id
                FROM People
                WHERE person_id = ?
                """,
                request.person_id
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Person not found."
                )

            cursor.execute(
                """
                UPDATE FaceEmbeddings
                SET is_active = 0
                WHERE person_id = ?
                  AND is_active = 1
                """,
                request.person_id
            )

            for pose in POSE_ORDER:
                embedding = sample_data[pose]

                embedding_bytes = embedding_service.serialize(
                    embedding
                )

                cursor.execute(
                    """
                    INSERT INTO FaceEmbeddings
                    (
                        person_id,
                        embedding,
                        embedding_dimension,
                        model_name,
                        is_active,
                        pose_label,
                        registration_id
                    )
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    request.person_id,
                    embedding_bytes,
                    len(embedding),
                    embedding_service.model_name,
                    pose,
                    registration_id
                )

            connection.commit()

        except HTTPException:
            if connection is not None:
                connection.rollback()
            raise

        except Exception:
            if connection is not None:
                connection.rollback()

            raise HTTPException(
                status_code=500,
                detail="Failed to save face registration."
            )

        finally:
            if connection is not None:
                connection.close()

        registration_session_manager.delete_session(session_id)

        return {
            "status": "saved",
            "message": "Face registration saved successfully.",
            "person_id": request.person_id,
            "registration_id": registration_id,
            "saved_count": len(POSE_ORDER),
            "saved_poses": POSE_ORDER
        }
        
@router.delete("/sessions/{session_id}")
def cancel_registration_session(session_id: str):
    deleted = registration_session_manager.delete_session(session_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Registration session not found or already expired."
        )

    return {
        "status": "cancelled",
        "message": "Registration session discarded successfully."
    }
