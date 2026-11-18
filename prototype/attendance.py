
import os

import cv2
import json
import numpy as np
import time
from insightface.app import FaceAnalysis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "students.json")

SIMILARITY_THRESHOLD = 0.45
INFERENCE_INTERVAL = 3
STABLE_MATCHES = 3

with open(DATABASE_PATH, "r") as file:
    students = json.load(file)

if not students:
    print("No registered students.")
    exit()

# Prepare all embeddings in one matrix

all_embeddings = []
embedding_owners = []

for student in students:
    for embedding in student["embeddings"]:
        all_embeddings.append(embedding)
        embedding_owners.append(student["id"])

embedding_matrix = np.asarray(
    all_embeddings,
    dtype=np.float32
)

embedding_owners = np.asarray(embedding_owners)

# Load AI models

app = FaceAnalysis(
    name="buffalo_l",
    allowed_modules=["detection", "recognition"],
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=-1, det_size=(320, 320))

camera = cv2.VideoCapture(0)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not camera.isOpened():
    print("Cannot open camera.")
    exit()

present_students = set()
candidate_counts = {}

cached_faces = []

frame_count = 0
inference_time = 0
start_time = time.perf_counter()

print("Attendance started. Press Q to exit.")

while True:
    ret, frame = camera.read()

    if not ret:
        break

    frame_count += 1

    # Run AI only every N frames

    if frame_count % INFERENCE_INTERVAL == 0:

        inference_start = time.perf_counter()

        faces = app.get(frame)

        inference_time = (
            time.perf_counter() - inference_start
        )

        cached_faces = []
        matched_students = set()

        for face in faces:

            x1, y1, x2, y2 = face.bbox.astype(int)

            current_embedding = face.normed_embedding

            # Compare against every registered embedding

            similarities = embedding_matrix @ current_embedding

            best_index = int(np.argmax(similarities))

            best_similarity = float(
                similarities[best_index]
            )

            student_id = embedding_owners[best_index]

            if best_similarity >= SIMILARITY_THRESHOLD:

                student = next(
                    item for item in students
                    if item["id"] == student_id
                )

                name = student["name"]
                color = (0, 255, 0)

                matched_students.add(student_id)

            else:
                name = "Unknown"
                color = (0, 0, 255)
                student_id = None

            cached_faces.append({
                "bbox": (x1, y1, x2, y2),
                "name": name,
                "similarity": best_similarity,
                "color": color
            })

        # Require stable recognition across consecutive
        # inference cycles before marking attendance.

        for student in students:

            student_id = student["id"]

            if student_id in present_students:
                continue

            if student_id in matched_students:
                candidate_counts[student_id] = (
                    candidate_counts.get(student_id, 0) + 1
                )
            else:
                candidate_counts[student_id] = 0

            if candidate_counts[student_id] >= STABLE_MATCHES:

                present_students.add(student_id)

                print(
                    f"Present: {student['name']} "
                    f"({student_id})"
                )

    # Draw cached results on the latest camera frame

    for result in cached_faces:

        x1, y1, x2, y2 = result["bbox"]

        label = (
            f"{result['name']} "
            f"({result['similarity']:.2f})"
        )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            result["color"],
            2
        )

        cv2.putText(
            frame,
            label,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            result["color"],
            2
        )

    elapsed = time.perf_counter() - start_time
    camera_fps = frame_count / elapsed if elapsed > 0 else 0

    cv2.putText(
        frame,
        f"Present: {len(present_students)}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"Camera FPS: {camera_fps:.1f}",
        (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"Inference: {inference_time * 1000:.0f} ms",
        (10, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 0),
        2
    )

    cv2.imshow("AI Attendance", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

print("\nAttendance Summary")

for student in students:

    if student["id"] in present_students:
        status = "Present"
    else:
        status = "Absent"

    print(f"{student['name']}: {status}")

print(
    f"\nTotal present: {len(present_students)}"
)
