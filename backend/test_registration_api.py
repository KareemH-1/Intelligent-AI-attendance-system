
import cv2
import requests
import time


API_URL = "http://127.0.0.1:8000/api/registration"


def create_session():
    response = requests.post(f"{API_URL}/sessions")
    response.raise_for_status()

    data = response.json()

    print("Registration session created.")
    print("Session ID:", data["session_id"])
    print("Current pose:", data["current_pose"])

    return data["session_id"]


def capture_frames(session_id):
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Could not open webcam.")
        return

    capture_url = f"{API_URL}/sessions/{session_id}/capture"

    print("\nFollow the pose instructions.")
    print("Press Q to cancel.\n")

    last_request_time = 0
    request_interval = 0.45

    current_pose = "FRONT"
    instruction = "Look straight at the camera"

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Could not read camera frame.")
                break

            display_frame = cv2.flip(frame, 1)

            cv2.putText(
                display_frame,
                f"Pose: {current_pose}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.putText(
                display_frame,
                instruction[:60],
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )

            cv2.imshow("Registration API Test", display_frame)

            current_time = time.monotonic()

            if current_time - last_request_time >= request_interval:
                last_request_time = current_time

                encode_success, encoded_frame = cv2.imencode(
                    ".jpg",
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 85]
                )

                if encode_success:
                    try:
                        response = requests.post(
                            capture_url,
                            files={
                                "file": (
                                    "frame.jpg",
                                    encoded_frame.tobytes(),
                                    "image/jpeg"
                                )
                            },
                            timeout=30
                        )

                        if response.status_code != 200:
                            print(
                                "API error:",
                                response.status_code,
                                response.text
                            )
                        else:
                            data = response.json()

                            print(
                                f"\r{data['status']}: {data['message']}",
                                end="",
                                flush=True
                            )

                            if "next_pose" in data:
                                current_pose = data["next_pose"]

                                if current_pose is None:
                                    print("\n\nAll poses captured!")

                                    print(
                                        "Verification:",
                                        data.get("verification")
                                    )
                                    break

                                instruction = data.get(
                                    "next_instruction",
                                    ""
                                )

                                print(
                                    f"\n\nNext pose: {current_pose}"
                                )

                    except requests.RequestException as error:
                        print("\nRequest failed:", error)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

        try:
            requests.delete(f"{API_URL}/sessions/{session_id}")
        except requests.RequestException:
            pass


if __name__ == "__main__":
    session_id = create_session()
    capture_frames(session_id)
