import { useCallback, useEffect, useRef, useState } from "react";
import {
  Camera,
  Check,
  CheckCircle2,
  Circle,
  LoaderCircle,
  RotateCcw,
  ShieldCheck,
  VideoOff,
} from "lucide-react";

import api from "../services/api";
import "./FaceRegistrationStep.css";

const POSES = [
  { id: "FRONT", label: "Look straight ahead" },
  { id: "LEFT", label: "Turn your head to the left" },
  { id: "RIGHT", label: "Turn your head to the right" },
  { id: "UP", label: "Look slightly upward" },
  { id: "DOWN", label: "Look slightly downward" },
];

export default function FaceRegistrationStep({
  personId,
  studentName,
  onComplete,
  onSkip,
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const sessionIdRef = useRef(null);
  const activeRef = useRef(true);
  const savedRef = useRef(false);
  const completeRef = useRef(false);

  const [captureVersion, setCaptureVersion] = useState(0);
  const [sessionId, setSessionId] = useState(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [currentPose, setCurrentPose] = useState("FRONT");
  const [instruction, setInstruction] = useState("");
  const [progress, setProgress] = useState({
    captured_poses: [],
    missing_poses: POSES.map((pose) => pose.id),
    captured_count: 0,
    required_count: 5,
    is_complete: false,
  });
  const [capturedPhotos, setCapturedPhotos] = useState([]);
  const [message, setMessage] = useState(
    "Position your face inside the guide.",
  );
  const [error, setError] = useState("");
  const [initializing, setInitializing] = useState(true);
  const [saving, setSaving] = useState(false);
  const [retaking, setRetaking] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const [registrationComplete, setRegistrationComplete] = useState(false);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCameraReady(false);
  }, []);

  useEffect(() => {
    activeRef.current = true;

    const initialize = async () => {
      let createdSessionId = null;

      try {
        setInitializing(true);
        setError("");

        const sessionResponse = await api.post("/registration/sessions");

        createdSessionId = sessionResponse.data.session_id;

        if (!activeRef.current) {
          await api.delete(`/registration/sessions/${createdSessionId}`);
          return;
        }

        sessionIdRef.current = createdSessionId;
        setSessionId(createdSessionId);
        setCurrentPose(sessionResponse.data.current_pose);
        setInstruction(sessionResponse.data.instruction);
        setProgress(sessionResponse.data.progress);

        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error(
            "Your browser does not support camera access. Please use a modern browser.",
          );
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: "user",
            width: { ideal: 640 },
            height: { ideal: 480 },
          },
        });

        if (!activeRef.current) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;

        const video = videoRef.current;

        if (!video) {
          throw new Error("Camera preview could not be initialized.");
        }

        video.srcObject = stream;
        await video.play();

        if (activeRef.current) {
          setCameraReady(true);
        }
      } catch (err) {
        if (!activeRef.current) {
          return;
        }

        setError(
          err.response?.data?.detail ||
            err.message ||
            "Could not initialize face registration.",
        );

        if (createdSessionId) {
          try {
            await api.delete(`/registration/sessions/${createdSessionId}`);
          } catch {
            // The session will expire automatically if deletion fails.
          }

          sessionIdRef.current = null;
          setSessionId(null);
        }

        stopCamera();
      } finally {
        if (activeRef.current) {
          setInitializing(false);
        }
      }
    };

    initialize();

    return () => {
      activeRef.current = false;

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      const activeSessionId = sessionIdRef.current;

      if (activeSessionId && !savedRef.current) {
        api.delete(`/registration/sessions/${activeSessionId}`).catch(() => {});
      }
    };
  }, [stopCamera]);

  useEffect(() => {
    if (!sessionId || !cameraReady) {
      return;
    }

    let cancelled = false;

    const delay = (milliseconds) =>
      new Promise((resolve) => setTimeout(resolve, milliseconds));

    const captureLoop = async () => {
      while (!cancelled && !completeRef.current) {
        const video = videoRef.current;
        const canvas = canvasRef.current;

        if (!video || !canvas || video.readyState < 2) {
          await delay(250);
          continue;
        }

        try {
          const context = canvas.getContext("2d");

          canvas.width = 640;
          canvas.height = 480;

          // Draw the original video frame without mirroring.
          context.drawImage(video, 0, 0, canvas.width, canvas.height);

          const blob = await new Promise((resolve) => {
            canvas.toBlob(resolve, "image/jpeg", 0.85);
          });

          if (!blob || cancelled) {
            await delay(250);
            continue;
          }

          const formData = new FormData();
          formData.append("file", blob, "face-frame.jpg");

          const response = await api.post(
            `/registration/sessions/${sessionId}/capture`,
            formData,
            {
              headers: {
                "Content-Type": undefined,
              },
            },
          );

          if (cancelled) {
            break;
          }

          const data = response.data;

          setMessage(data.message || "Analyzing your face...");
          setProgress(data.registration_progress);

          if (data.next_pose) {
            setCurrentPose(data.next_pose);
            setInstruction(data.next_instruction || "");
          }

          if (data.registration_progress?.is_complete || data.verification) {
            let photos = data.captured_photos;

            // Recover the photos if the capture response did not include them.
            if (!photos || photos.length !== 5) {
              try {
                const sessionResponse = await api.get(
                  `/registration/sessions/${sessionId}`,
                );

                photos = sessionResponse.data.captured_photos;
              } catch {
                photos = [];
              }
            }

            completeRef.current = true;
            setCapturedPhotos(photos || []);
            setRegistrationComplete(true);

            setMessage(
              data.verification?.message ||
                "All five face poses have been captured.",
            );

            break;
          }
        } catch (err) {
          if (cancelled) {
            break;
          }

          setMessage(
            err.response?.data?.detail ||
              "Unable to process the camera frame. Retrying...",
          );

          if (err.response?.status === 404) {
            setError(
              "Your registration session has expired. Close this step and start again.",
            );
            break;
          }
        }

        // Wait for the next frame only after the previous request finishes.
        await delay(250);
      }
    };

    captureLoop();

    return () => {
      cancelled = true;
    };
  }, [sessionId, cameraReady, captureVersion]);

  const handleRetake = async (pose) => {
    if (!sessionId || retaking || saving) {
      return;
    }

    try {
      setRetaking(true);
      setError("");
      setMessage(`Preparing to recapture ${pose.toLowerCase()} pose...`);

      const response = await api.post(
        `/registration/sessions/${sessionId}/retake/${pose}`,
      );

      completeRef.current = false;
      setCaptureVersion((previous) => previous + 1);
      setRegistrationComplete(false);
      setCapturedPhotos([]);
      setCurrentPose(response.data.pose);
      setInstruction(response.data.instruction);
      setProgress(response.data.progress);
      setMessage("Follow the positioning instruction to capture this pose.");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not restart this pose.");
    } finally {
      setRetaking(false);
    }
  };

  const handleSave = async () => {
    if (!sessionId || !registrationComplete || saving) {
      return;
    }

    try {
      setSaving(true);
      setError("");

      await api.post(`/registration/sessions/${sessionId}/save`, {
        person_id: personId,
      });

      savedRef.current = true;
      sessionIdRef.current = null;

      stopCamera();
      onComplete();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Failed to save face registration. Please try again.",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSkip = async () => {
    if (skipping || saving) {
      return;
    }

    try {
      setSkipping(true);

      if (sessionId) {
        await api.delete(`/registration/sessions/${sessionId}`);
      }

      savedRef.current = true;
      sessionIdRef.current = null;

      stopCamera();
      onSkip();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Could not close the registration session.",
      );
    } finally {
      setSkipping(false);
    }
  };

  const capturedCount = progress?.captured_count || 0;
  const percentage = (capturedCount / 5) * 100;

  return (
    <div className="face-registration">
      <div className="face-registration__intro">
        <div className="face-registration__student">
          <div className="face-registration__student-icon">
            <Camera size={19} />
          </div>

          <div>
            <span className="face-registration__eyebrow">FACE ENROLLMENT</span>
            <h3>{studentName}</h3>
            <p>Student ID: {personId}</p>
          </div>
        </div>

        <div className="face-registration__counter">
          <strong>{capturedCount}</strong>
          <span>/ 5 poses</span>
        </div>
      </div>

      <div className="face-registration__progress">
        <div
          className="face-registration__progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="face-registration__workspace">
        <div className="face-registration__camera-column">
          <div className="face-registration__camera">
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="face-registration__video"
            />

            <div className="face-registration__guide">
              <div className="face-registration__oval" />
              <span>POSITION YOUR FACE HERE</span>
            </div>

            {initializing && (
              <div className="face-registration__camera-overlay">
                <LoaderCircle size={28} className="spin" />
                <span>Starting camera...</span>
              </div>
            )}

            {!initializing && !cameraReady && (
              <div className="face-registration__camera-overlay">
                <VideoOff size={30} />
                <span>Camera unavailable</span>
              </div>
            )}

            {cameraReady && (
              <div className="face-registration__camera-live">
                <span />
                Camera active
              </div>
            )}
          </div>

          <canvas ref={canvasRef} className="face-registration__canvas" />

          <div className="face-registration__feedback">
            <div className="face-registration__feedback-icon">
              {registrationComplete ? (
                <CheckCircle2 size={19} />
              ) : (
                <Camera size={19} />
              )}
            </div>

            <p>{message}</p>
          </div>

          {error && (
            <div className="face-registration__error" role="alert">
              {error}
            </div>
          )}
        </div>

        <aside className="face-registration__side">
          <div className="face-registration__instruction">
            <span className="face-registration__eyebrow">
              CURRENT INSTRUCTION
            </span>

            <h3>
              {registrationComplete
                ? "Capture complete"
                : POSES.find((pose) => pose.id === currentPose)?.label}
            </h3>

            <p>
              {registrationComplete
                ? "All five poses have been captured. You can now save the registration."
                : instruction || "Keep your face centered inside the guide."}
            </p>
          </div>

          <div className="face-registration__pose-list">
            {POSES.map((pose, index) => {
              const captured = progress.captured_poses?.includes(pose.id);
              const active = currentPose === pose.id && !registrationComplete;

              return (
                <div
                  key={pose.id}
                  className={`face-registration__pose ${
                    active ? "is-active" : ""
                  } ${captured ? "is-captured" : ""}`}
                >
                  <div className="face-registration__pose-icon">
                    {captured ? <Check size={15} /> : <Circle size={15} />}
                  </div>

                  <div className="face-registration__pose-info">
                    <strong>{pose.id}</strong>
                    <span>{pose.label}</span>
                  </div>

                  {captured && (
                    <button
                      type="button"
                      className="face-registration__retake"
                      onClick={() => handleRetake(pose.id)}
                      disabled={!registrationComplete || saving || retaking}
                    >
                      <RotateCcw size={14} />
                      Retake
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <div className="face-registration__note">
            <ShieldCheck size={17} />
            <p>
              Make sure your face is clearly visible and the lighting is
              adequate. Avoid moving too quickly between poses.
            </p>
          </div>
        </aside>
      </div>
      {registrationComplete && (
        <section className="face-registration__gallery">
          <div className="face-registration__gallery-header">
            <div>
              <span className="face-registration__eyebrow">CAPTURE REVIEW</span>
              <h3>Registered face samples</h3>
              <p>
                Review the five captured positions before saving the
                registration.
              </p>
            </div>

            <div className="face-registration__gallery-count">
              <CheckCircle2 size={16} />
              {capturedPhotos.length} / 5 captured
            </div>
          </div>

          {capturedPhotos.length === 5 ? (
            <div className="face-registration__gallery-grid">
              {capturedPhotos.map((photo) => {
                const [x1, y1, x2, y2] = photo.bbox;

                const left = (x1 / 640) * 100;
                const top = (y1 / 480) * 100;
                const width = ((x2 - x1) / 640) * 100;
                const height = ((y2 - y1) / 480) * 100;

                return (
                  <article
                    className="face-registration__photo-card"
                    key={photo.pose_name}
                  >
                    <div className="face-registration__photo">
                      <img
                        src={photo.image}
                        alt={`${photo.pose_name} face capture`}
                      />

                      <div
                        className="face-registration__face-box"
                        style={{
                          left: `${left}%`,
                          top: `${top}%`,
                          width: `${width}%`,
                          height: `${height}%`,
                        }}
                      />
                    </div>

                    <div className="face-registration__photo-info">
                      <div>
                        <strong>{photo.pose_name}</strong>
                        <span>
                          {
                            POSES.find((pose) => pose.id === photo.pose_name)
                              ?.label
                          }
                        </span>
                      </div>

                      <button
                        type="button"
                        className="face-registration__photo-retake"
                        onClick={() => handleRetake(photo.pose_name)}
                        disabled={saving || retaking}
                      >
                        <RotateCcw size={14} />
                        Retake
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="face-registration__gallery-error">
              <p>
                The five captured photos could not be loaded. Please refresh the
                registration session or restart capture.
              </p>
            </div>
          )}
        </section>
      )}
      <div className="face-registration__footer">
        <button
          type="button"
          className="btn btn--secondary"
          onClick={handleSkip}
          disabled={saving || skipping}
        >
          {skipping ? "Skipping..." : "Skip for now"}
        </button>

        <button
          type="button"
          className="btn btn--primary"
          onClick={handleSave}
          disabled={
            !registrationComplete ||
            capturedPhotos.length !== 5 ||
            saving ||
            retaking
          }
        >
          {saving ? "Saving face data..." : "Save Face Registration"}
        </button>
      </div>
    </div>
  );
}
