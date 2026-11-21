
import cv2

from vision_layer.registration_service import registration_service
from vision_layer.sample_collector import SampleCollector
from vision_layer.registration_verifier import registration_verifier

POSES = [
    "FRONT",
    "LEFT",
    "RIGHT",
    "UP",
    "DOWN"
]

POSE_INSTRUCTIONS = {
    "FRONT": "Look straight at the camera",
    "LEFT": "Turn your head slightly LEFT",
    "RIGHT": "Turn your head slightly RIGHT",
    "UP": "Look slightly UP",
    "DOWN": "Look slightly DOWN"
}


collector = SampleCollector(
    required_frames=8,
    stability_duration=0.8,
    max_frame_gap=0.5
)

current_pose_index = 0
current_pose = POSES[current_pose_index]

collector.start_pose(current_pose)

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera.")
    exit()


print("Camera opened successfully.")
print("Follow the instructions displayed on screen.")
print("Press R to retake the current pose.")
print("Press Q to quit.")


try:
    while True:
        success, frame = camera.read()

        if not success:
            print("Failed to read camera frame.")
            break

        current_pose = POSES[current_pose_index]

        frame_result = registration_service.evaluate_frame(
            frame,
            current_pose
        )

        capture_result = collector.update(frame_result)

        display_frame = cv2.flip(frame, 1)

        # Display current pose and instruction.
        cv2.putText(
            display_frame,
            f"Pose: {current_pose}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.putText(
            display_frame,
            POSE_INSTRUCTIONS[current_pose],
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # Display frame validation feedback.
        feedback_color = (
            (0, 255, 0)
            if frame_result.is_valid
            else (0, 0, 255)
        )

        cv2.putText(
            display_frame,
            capture_result.message,
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            feedback_color,
            2
        )

        # Display capture progress.
        bar_x = 20
        bar_y = 150
        bar_width = 300
        bar_height = 18

        cv2.rectangle(
            display_frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (100, 100, 100),
            2
        )

        progress_width = int(
            bar_width * capture_result.progress / 100
        )

        cv2.rectangle(
            display_frame,
            (bar_x, bar_y),
            (bar_x + progress_width, bar_y + bar_height),
            (0, 200, 0),
            -1
        )

        # Display overall registration progress.
        completed_count = len(collector.samples.embeddings)

        cv2.putText(
            display_frame,
            f"Completed poses: {completed_count}/5",
            (20, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.imshow("Face Registration Test", display_frame)

        # Automatically advance after successful capture.
        if capture_result.is_captured:
            print(capture_result.message)

            current_pose_index += 1

            if current_pose_index >= len(POSES):
                print("\nAll five poses captured successfully.")
                break

            current_pose = POSES[current_pose_index]
            collector.start_pose(current_pose)

            print(
                f"\nNext pose: {current_pose} - "
                f"{POSE_INSTRUCTIONS[current_pose]}"
            )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("\nRegistration cancelled.")
            break

        elif key == ord("r"):
            collector.retake(current_pose)

            print(f"\nRetaking pose: {current_pose}")

finally:
    camera.release()
    cv2.destroyAllWindows()


print("\nRegistration results:")

for pose_name in POSES:
    if pose_name in collector.samples.embeddings:
        embedding = collector.samples.embeddings[pose_name]

        print(
            f"{pose_name}: Captured | "
            f"Embedding shape: {embedding.shape}"
        )
    else:
        print(f"{pose_name}: Not captured")

print("\nRegistration complete:", collector.is_complete())


if collector.is_complete():
    print("\nRunning registration verification...")

    samples = collector.get_samples()

    verification_result = registration_verifier.verify_samples(
        samples
    )

    print("\nVerification status:", verification_result.status)
    print("Message:", verification_result.message)

    print("\nReal face embedding similarities:")

    for pair_name, similarity in verification_result.similarities.items():
        print(f"{pair_name}: {similarity:.4f}")

    print("\nVerification passed:", verification_result.is_valid)

else:
    print("\nRegistration verification skipped.")
    print("All five poses must be captured first.")