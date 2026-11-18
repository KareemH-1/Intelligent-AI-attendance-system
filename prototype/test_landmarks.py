
import cv2
from insightface.app import FaceAnalysis

app = FaceAnalysis(
    name="buffalo_l",
    allowed_modules=["detection", "recognition"],
    providers=["CPUExecutionProvider"]
)

app.prepare(ctx_id=-1, det_size=(320, 320))

camera = cv2.VideoCapture(0)

while True:
    ret, frame = camera.read()

    if not ret:
        break

    faces = app.get(frame)
    display = frame.copy()

    if len(faces) == 1:
        landmarks = faces[0].kps

        for i, point in enumerate(landmarks):
            x, y = point.astype(int)

            cv2.circle(display, (x, y), 4, (0, 255, 0), -1)
            cv2.putText(
                display,
                str(i),
                (x + 5, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1
            )

        print(
            "Landmarks:",
            landmarks.round(2).tolist()
        )

    cv2.imshow("Landmark Diagnostic", display)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
