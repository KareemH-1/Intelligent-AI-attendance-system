
import cv2
import json
import os
import numpy as np
from insightface.app import FaceAnalysis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "students.json")



SAMPLES_REQUIRED = 5
VERIFICATION_THRESHOLD = 0.45
MIN_FACE_SIZE = 100
MIN_SHARPNESS = 15

POSES = [
    "FRONT",
    "LEFT",
    "RIGHT",
    "UP",
    "DOWN"
]
def estimate_pose(face, frame):
    landmarks = face.kps

    left_eye = landmarks[0]
    right_eye = landmarks[1]
    nose = landmarks[2]
    left_mouth = landmarks[3]
    right_mouth = landmarks[4]

    eye_center = (left_eye + right_eye) / 2
    mouth_center = (left_mouth + right_mouth) / 2

    face_width = np.linalg.norm(right_eye - left_eye)
    vertical_distance = mouth_center[1] - eye_center[1]

    if face_width == 0 or vertical_distance == 0:
        return None, None

    yaw = (nose[0] - eye_center[0]) / face_width

    pitch = (
        (nose[1] - eye_center[1]) / vertical_distance
    )

    return yaw, pitch

def valid_pose(pose, yaw, pitch):
    if yaw is None or pitch is None:
        return False

    if pose == "FRONT":
        return abs(yaw) < 0.12 and 0.45 < pitch < 0.70

    if pose == "LEFT":
        return yaw < -0.18

    if pose == "RIGHT":
        return yaw > 0.18

    if pose == "UP":
        return pitch < 0.45

    if pose == "DOWN":
        return pitch > 0.60

    return False
def is_sharp(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    sharpness = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()


    return sharpness >= MIN_SHARPNESS


def load_students():
    os.makedirs(DATABASE_DIR, exist_ok=True)

    if not os.path.exists(DATABASE_PATH):
        with open(DATABASE_PATH, "w") as file:
            json.dump([], file)
        return []

    with open(DATABASE_PATH, "r") as file:
        content = file.read().strip()

        if not content:
            return []

        return json.loads(content)

def save_students(students):
    with open(DATABASE_PATH, "w") as file:
        json.dump(students, file, indent=4)


def create_preview(samples):
    width = 250
    height = 190

    preview = np.zeros(
        (height * 2, width * 3, 3),
        dtype=np.uint8
    )

    for index, sample in enumerate(samples):
        image = cv2.resize(
            sample["image"],
            (width, height)
        )

        row = index // 3
        col = index % 3

        y = row * height
        x = col * width

        preview[y:y + height, x:x + width] = image

        cv2.putText(
            preview,
            sample["pose"],
            (x + 10, y + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

    return preview


students = load_students()

student_id = input("Student ID: ").strip()
student_name = input("Student name: ").strip()

if not student_id or not student_name:
    print("Student ID and name are required.")
    exit()

for student in students:
    if student["id"] == student_id:
        print("Student already registered.")
        exit()

app = FaceAnalysis(
    name="buffalo_l",
    allowed_modules=["detection", "recognition"],
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=-1, det_size=(320, 320))

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open camera.")
    exit()

samples = []
current_pose = 0

print("\nFollow the instructions on screen.")
print("Press S to capture.")
print("Press Q to cancel.")

while current_pose < SAMPLES_REQUIRED:
    ret, frame = camera.read()

    if not ret:
        break

    faces = app.get(frame)

    display = frame.copy()

    pose = POSES[current_pose]

    cv2.putText(
        display,
        f"POSE: {pose}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

    cv2.putText(
        display,
        f"Progress: {current_pose}/5",
        (10, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )

    yaw = None
    pitch = None
    ready = False

    if len(faces) == 1:
        face = faces[0]

        x1, y1, x2, y2 = face.bbox.astype(int)

        face_width = x2 - x1
        face_height = y2 - y1

        yaw, pitch = estimate_pose(face, frame)

        crop = frame[
            max(0, y1):min(frame.shape[0], y2),
            max(0, x1):min(frame.shape[1], x2)
        ]

        if crop.size > 0:
            size_ok = face_width >= MIN_FACE_SIZE and face_height >= MIN_FACE_SIZE
            sharpness_ok = is_sharp(crop)
            pose_ok = valid_pose(pose, yaw, pitch)

            ready = size_ok and sharpness_ok and pose_ok

            cv2.putText(
                display,
                f"Size: {face_width}x{face_height} | Sharp: {sharpness_ok} | Pose: {pose_ok}",
                (10, 135),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 0),
                2
            )

        color = (0, 255, 0) if ready else (0, 0, 255)

        cv2.rectangle(
            display,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        if yaw is not None:
            cv2.putText(
                display,
                f"Yaw: {yaw:.2f} Pitch: {pitch:.2f}",
                (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

    elif len(faces) == 0:
        cv2.putText(
            display,
            "No face detected",
            (10, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2
        )

    else:
        cv2.putText(
            display,
            "Only one person allowed",
            (10, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2
        )

    status = "READY - Press S" if ready else "Adjust your position"

    cv2.putText(
        display,
        status,
        (10, display.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0) if ready else (0, 0, 255),
        2
    )

    cv2.imshow("Registration", display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    if key == ord("s"):
        if not ready:
            print("Invalid pose or poor image quality.")
            continue

        face = faces[0]

        x1, y1, x2, y2 = face.bbox.astype(int)

        crop = frame[
            max(0, y1):min(frame.shape[0], y2),
            max(0, x1):min(frame.shape[1], x2)
        ].copy()

        samples.append({
            "pose": pose,
            "embedding": face.normed_embedding.tolist(),
            "image": crop
        })

        print(f"Captured {pose}")

        current_pose += 1

camera.release()
cv2.destroyAllWindows()

if len(samples) != SAMPLES_REQUIRED:
    print("Registration cancelled. Not all poses were captured.")
    exit()


preview = create_preview(samples)

cv2.imshow("Review Registration Photos", preview)

print("\nReview the five captured photos.")
print("Y = Confirm, R = Retake, Q = Cancel")

while True:
    key = cv2.waitKey(0) & 0xFF

    if key == ord("y"):
        confirmed = True
        break

    if key == ord("r"):
        confirmed = False
        break

    if key == ord("q"):
        confirmed = None
        break

cv2.destroyAllWindows()

if confirmed is None:
    print("Registration cancelled.")
    exit()

if not confirmed:
    print("Please run registration again.")
    exit()


print("\nRegistration verification.")
print("Look directly at the camera and press S.")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Cannot open camera.")
    exit()

reference_embeddings = np.array(
    [sample["embedding"] for sample in samples],
    dtype=np.float32
)

verified = False

while True:
    ret, frame = camera.read()

    if not ret:
        break

    faces = app.get(frame)

    display = frame.copy()

    cv2.putText(
        display,
        "Look at the camera and press S",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )

    cv2.imshow("Identity Verification", display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    if key == ord("s"):
        if len(faces) != 1:
            print("Exactly one face is required.")
            continue

        test_embedding = faces[0].normed_embedding

        similarities = reference_embeddings @ test_embedding

        best_similarity = float(np.max(similarities))

        print(f"Verification similarity: {best_similarity:.3f}")

        if best_similarity >= VERIFICATION_THRESHOLD:
            verified = True
            break

        print("Verification failed. Try again.")

camera.release()
cv2.destroyAllWindows()

if not verified:
    print("Registration failed. Student was not saved.")
    exit()


students.append({
    "id": student_id,
    "name": student_name,
    "embeddings": [
        sample["embedding"] for sample in samples
    ]
})

save_students(students)

print("\nRegistration successful!")
print(f"Student: {student_name}")
print(f"Samples: {len(samples)}")
