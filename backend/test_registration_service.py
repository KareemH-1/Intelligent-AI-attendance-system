
import cv2

from vision_layer.registration_service import registration_service


camera = cv2.VideoCapture(0)

if not camera.isOpened():
    raise RuntimeError("Could not open camera.")

expected_pose = "FRONT"

try:
    while True:

        success, frame = camera.read()

        if not success:
            break

        result = registration_service.evaluate_frame(
            frame,
            expected_pose
        )

        display = cv2.flip(frame, 1)

        color = (
            (0, 255, 0)
            if result.is_valid
            else (0, 0, 255)
        )

        cv2.putText(
            display,
            f"Expected: {expected_pose}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.putText(
            display,
            result.status,
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2
        )

        cv2.putText(
            display,
            result.message,
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2
        )

        if result.yaw is not None:
            cv2.putText(
                display,
                f"Yaw: {result.yaw:.1f}",
                (20, 155),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        if result.pitch is not None:
            cv2.putText(
                display,
                f"Pitch: {result.pitch:.1f}",
                (20, 190),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        cv2.imshow("Registration Frame Evaluation", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("1"):
            expected_pose = "FRONT"

        elif key == ord("2"):
            expected_pose = "LEFT"

        elif key == ord("3"):
            expected_pose = "RIGHT"

        elif key == ord("4"):
            expected_pose = "UP"

        elif key == ord("5"):
            expected_pose = "DOWN"

        elif key == ord("q"):
            break

finally:
    camera.release()
    cv2.destroyAllWindows()
