import { useCallback, useEffect, useState } from "react";
import { History, Search, Eye, Users, CheckCircle2, XCircle, X } from "lucide-react";

import api from "../../services/api";

function getErrorDetail(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join(" ");
  }
  return fallback;
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function SessionHistoryPage() {
  const [semesters, setSemesters] = useState([]);
  const [halls, setHalls] = useState([]);
  const [semesterId, setSemesterId] = useState("");
  const [hallId, setHallId] = useState("");
  const [search, setSearch] = useState("");
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [selectedSession, setSelectedSession] = useState(null);
  const [studentRows, setStudentRows] = useState([]);
  const [studentLoading, setStudentLoading] = useState(false);
  const limit = 20;

  useEffect(() => {
    Promise.all([api.get("/semesters"), api.get("/halls")])
      .then(([semesterResponse, hallResponse]) => {
        setSemesters(semesterResponse.data);
        setHalls(hallResponse.data);
        const active = semesterResponse.data.find((semester) => semester.is_active);
        if (active) setSemesterId(String(active.semester_id));
      })
      .catch((error) => {
        setPageError(getErrorDetail(error, "Failed to load session filters."));
      });
  }, []);

  const loadHistory = useCallback(async () => {
    if (!semesterId) return;
    setLoading(true);
    setPageError("");
    try {
      const response = await api.get("/timetable/sessions/history", {
        params: {
          semester_id: semesterId,
          hall_id: hallId || undefined,
          search,
          limit,
          offset,
        },
      });
      setSessions(response.data.items);
      setTotal(response.data.total);
    } catch (error) {
      setPageError(getErrorDetail(error, "Failed to load session history."));
    } finally {
      setLoading(false);
    }
  }, [semesterId, hallId, search, offset]);

  useEffect(() => {
    const timeoutId = setTimeout(loadHistory, 300);
    return () => clearTimeout(timeoutId);
  }, [loadHistory]);

  const openSessionDetails = async (session) => {
    setSelectedSession(session);
    setStudentRows([]);
    setStudentLoading(true);
    try {
      const response = await api.get(
        `/timetable/sessions/${session.session_id}/students`,
      );
      setStudentRows(response.data);
    } catch (error) {
      setPageError(getErrorDetail(error, "Failed to load attendance details."));
    } finally {
      setStudentLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Hall Session History</h1>
            <p className="text-muted">
              Review completed and past hall course sessions across the semester.
            </p>
          </div>
        </div>

        {pageError && (
          <div className="alert alert--error">
            <div className="alert__body">{pageError}</div>
          </div>
        )}

        <section className="section">
          <div className="toolbar session-history-toolbar">
            <label className="form-field">
              <span>Semester</span>
              <select
                className="select"
                value={semesterId}
                onChange={(event) => {
                  setSemesterId(event.target.value);
                  setOffset(0);
                }}
              >
                <option value="">Select semester</option>
                {semesters.map((semester) => (
                  <option key={semester.semester_id} value={semester.semester_id}>
                    {semester.semester_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Lecture Hall</span>
              <select
                className="select"
                value={hallId}
                onChange={(event) => {
                  setHallId(event.target.value);
                  setOffset(0);
                }}
              >
                <option value="">All halls</option>
                {halls.map((hall) => (
                  <option key={hall.hall_id} value={hall.hall_id}>
                    {hall.hall_name} — {hall.building}
                  </option>
                ))}
              </select>
            </label>

            <div className="search">
              <Search size={18} className="search__icon" />
              <input
                className="input"
                type="text"
                role="searchbox"
                placeholder="Search course, hall or lecturer..."
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setOffset(0);
                }}
              />
            </div>

            <span className="text-sm text-muted">
              {total} session{total === 1 ? "" : "s"}
            </span>
          </div>

          <div className="card">
            {loading ? (
              <div className="loading-state">
                <div className="spinner" />
                <p>Loading session history...</p>
              </div>
            ) : sessions.length === 0 ? (
              <div className="empty-state">
                <History size={28} />
                <h3>No past sessions found</h3>
                <p>Try changing the semester, hall or search.</p>
              </div>
            ) : (
              <>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Course</th>
                        <th>Hall</th>
                        <th>Lecturer</th>
                        <th>Attendance</th>
                        <th>Lecturer</th>
                        <th>Status</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((session) => (
                        <tr key={session.session_id}>
                          <td>
                            <strong>{formatDate(session.session_date)}</strong>
                            <div className="text-sm text-muted">
                              {session.scheduled_start}–{session.scheduled_end}
                            </div>
                          </td>
                          <td>
                            <strong>{session.course_code}</strong>
                            <div className="text-sm text-muted">
                              {session.course_name}
                            </div>
                          </td>
                          <td>
                            {session.hall_name}
                            <div className="text-sm text-muted">
                              {session.building}
                            </div>
                          </td>
                          <td>
                            {session.lecturer_name}
                            {session.ta_name && (
                              <div className="text-sm text-muted">
                                TA: {session.ta_name}
                              </div>
                            )}
                          </td>
                          <td>
                            <span className="badge badge--primary">
                              <Users size={12} />
                              {session.student_attendance_count}
                            </span>
                            <div className="text-sm text-muted">
                              {session.present_count} present · {session.late_count} late
                            </div>
                          </td>
                          <td>
                            {session.lecturer_attended ? (
                              <span className="badge badge--success">
                                <CheckCircle2 size={12} /> Attended
                              </span>
                            ) : (
                              <span className="badge badge--error">
                                <XCircle size={12} /> Not attended
                              </span>
                            )}
                          </td>
                          <td>{session.session_status}</td>
                          <td>
                            <button
                              type="button"
                              className="btn btn--ghost btn--icon"
                              title="View attendance"
                              onClick={() => openSessionDetails(session)}
                            >
                              <Eye size={16} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="table-footer">
                  <span>
                    Showing {sessions.length === 0 ? 0 : offset + 1}–
                    {Math.min(offset + sessions.length, total)} of {total}
                  </span>
                  <div className="action-group">
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      disabled={offset === 0}
                      onClick={() => setOffset((previous) => Math.max(0, previous - limit))}
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      disabled={offset + limit >= total}
                      onClick={() => setOffset((previous) => previous + limit)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </section>
      </div>

      {selectedSession && (
        <div className="modal-backdrop">
          <div className="modal modal--lg" role="dialog" aria-modal="true">
            <div className="modal__header">
              <div>
                <h2 className="modal__title">Session Attendance</h2>
                <p className="text-sm text-muted">
                  {selectedSession.course_code} · {formatDate(selectedSession.session_date)} · {selectedSession.hall_name}
                </p>
              </div>
              <button
                type="button"
                className="btn btn--ghost btn--icon"
                onClick={() => setSelectedSession(null)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>
            <div className="modal__body">
              {studentLoading ? (
                <div className="loading-state"><div className="spinner" /></div>
              ) : (
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>University ID</th>
                        <th>Student</th>
                        <th>Status</th>
                        <th>Check-in</th>
                        <th>Method</th>
                      </tr>
                    </thead>
                    <tbody>
                      {studentRows.map((student) => (
                        <tr key={student.attendance_id}>
                          <td className="mono">{student.university_id}</td>
                          <td>{student.full_name}</td>
                          <td>{student.attendance_status}</td>
                          <td>{new Date(student.check_in_time).toLocaleString()}</td>
                          <td>{student.verification_method}</td>
                        </tr>
                      ))}
                      {studentRows.length === 0 && (
                        <tr><td colSpan="5"><div className="empty-state">No student attendance records for this session.</div></td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
