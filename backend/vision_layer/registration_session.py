
from dataclasses import dataclass, field
import threading
import time
from uuid import uuid4

from vision_layer.sample_collector import SampleCollector


@dataclass
class RegistrationSession:
    session_id: str
    collector: SampleCollector
    created_at: float
    last_activity: float
    lock: threading.RLock = field(
        default_factory=threading.RLock,
        repr=False
    )


class RegistrationSessionManager:

    def __init__(
        self,
        expiration_seconds=900,
        max_sessions=100
    ):
        self.expiration_seconds = expiration_seconds
        self.max_sessions = max_sessions

        self._sessions = {}
        self._lock = threading.RLock()

    def _cleanup_expired_locked(self):
        now = time.monotonic()
        expired_sessions = []

        for session_id, session in self._sessions.items():
            if now - session.last_activity >= self.expiration_seconds:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self._sessions[session_id]

        return len(expired_sessions)

    def create_session(self):
        with self._lock:
            self._cleanup_expired_locked()

            if len(self._sessions) >= self.max_sessions:
                raise RuntimeError(
                    "Maximum number of active registration sessions reached."
                )

            now = time.monotonic()
            session_id = str(uuid4())

            session = RegistrationSession(
                session_id=session_id,
                collector=SampleCollector(),
                created_at=now,
                last_activity=now
            )

            self._sessions[session_id] = session

            return session

    def get_session(self, session_id):
        with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            now = time.monotonic()

            if now - session.last_activity >= self.expiration_seconds:
                del self._sessions[session_id]
                return None

            session.last_activity = now

            return session

    def delete_session(self, session_id):
        with self._lock:
            session = self._sessions.pop(session_id, None)

            return session is not None

    def cleanup_expired(self):
        with self._lock:
            return self._cleanup_expired_locked()

    def get_active_session_count(self):
        with self._lock:
            self._cleanup_expired_locked()

            return len(self._sessions)


registration_session_manager = RegistrationSessionManager()
