import { useCallback, useEffect, useState } from "react";
import { CalendarDays, Plus, Search, Pencil, Trash2, X, Clock3 } from "lucide-react";

import api from "../../services/api";

const days = [
  { value: 1, label: "Saturday" },
  { value: 2, label: "Sunday" },
  { value: 3, label: "Monday" },
  { value: 4, label: "Tuesday" },
  { value: 5, label: "Wednesday" },
  { value: 6, label: "Thursday" },
  { value: 7, label: "Friday" },
];

const emptySlot = {
  offering_id: "",
  instructor_role: "Lecturer",
  instructor_id: "",
  day_of_week: "1",
  start_time: "08:00",
  end_time: "09:30",
};

function getErrorDetail(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join(" ");
  }
  return fallback;
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (!hours) return `${remainder} min`;
  if (!remainder) return `${hours} hr`;
  return `${hours} hr ${remainder} min`;
}

function durationOf(start, end) {
  const [startHour, startMinute] = start.split(":").map(Number);
  const [endHour, endMinute] = end.split(":").map(Number);
  return endHour * 60 + endMinute - (startHour * 60 + startMinute);
}

export default function TimetablePage() {
  const [semesters, setSemesters] = useState([]);
  const [halls, setHalls] = useState([]);
  const [semesterId, setSemesterId] = useState("");
  const [hallId, setHallId] = useState("");
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSlot, setEditingSlot] = useState(null);
  const [formData, setFormData] = useState(emptySlot);
  const [formError, setFormError] = useState("");
  const [offeringSearch, setOfferingSearch] = useState("");
  const [offeringOffset, setOfferingOffset] = useState(0);
  const [offerings, setOfferings] = useState([]);
  const [offeringTotal, setOfferingTotal] = useState(0);
  const [lecturers, setLecturers] = useState([]);
  const [tas, setTas] = useState([]);
  const [deleteSlot, setDeleteSlot] = useState(null);
  const offeringLimit = 20;

  useEffect(() => {
    Promise.all([api.get("/semesters"), api.get("/halls")])
      .then(([semesterResponse, hallResponse]) => {
        setSemesters(semesterResponse.data);
        setHalls(hallResponse.data);
        const active = semesterResponse.data.find((semester) => semester.is_active);
        if (active) setSemesterId(String(active.semester_id));
        if (hallResponse.data[0]) setHallId(String(hallResponse.data[0].hall_id));
      })
      .catch((error) => {
        setPageError(getErrorDetail(error, "Failed to load schedule options."));
      });
  }, []);

  const loadSlots = useCallback(async () => {
    if (!semesterId || !hallId) return;
    setLoading(true);
    setPageError("");
    try {
      const response = await api.get("/timetable/weekly", {
        params: {
          semester_id: semesterId,
          hall_id: hallId,
        },
      });
      setSlots(response.data);
    } catch (error) {
      setPageError(getErrorDetail(error, "Failed to load the weekly timetable."));
    } finally {
      setLoading(false);
    }
  }, [semesterId, hallId]);

  useEffect(() => {
    loadSlots();
  }, [loadSlots]);

  const loadOfferings = useCallback(async () => {
    if (!semesterId) return;
    try {
      const response = await api.get("/timetable/offerings", {
        params: {
          semester_id: semesterId,
          search: offeringSearch,
          limit: offeringLimit,
          offset: offeringOffset,
        },
      });
      setOfferings(response.data.items);
      setOfferingTotal(response.data.total);
    } catch (error) {
      setFormError(getErrorDetail(error, "Failed to load course offerings."));
    }
  }, [semesterId, offeringSearch, offeringOffset]);

  useEffect(() => {
    if (!modalOpen) return;
    const timeoutId = setTimeout(loadOfferings, 300);
    return () => clearTimeout(timeoutId);
  }, [loadOfferings, modalOpen]);

  useEffect(() => {
    if (!formData.offering_id) {
      setLecturers([]);
      setTas([]);
      return;
    }
    api.get(`/timetable/offerings/${formData.offering_id}/instructors`)
      .then((response) => {
        setLecturers(response.data.lecturers);
        setTas(response.data.tas);
      })
      .catch((error) => {
        setFormError(getErrorDetail(error, "Failed to load assigned instructors."));
      });
  }, [formData.offering_id]);

  const openCreateModal = (dayOfWeek = 1) => {
    setEditingSlot(null);
    setFormData({ ...emptySlot, day_of_week: String(dayOfWeek) });
    setOfferingSearch("");
    setOfferingOffset(0);
    setLecturers([]);
    setTas([]);
    setFormError("");
    setModalOpen(true);
  };

  const openEditModal = (slot) => {
    setEditingSlot(slot);
    setFormData({
      offering_id: String(slot.offering_id),
      instructor_role: slot.ta_instructor_id ? "TA" : "Lecturer",
      instructor_id: String(slot.primary_instructor_id),
      day_of_week: String(slot.day_of_week),
      start_time: slot.start_time,
      end_time: slot.end_time,
    });
    setOfferingSearch("");
    setOfferingOffset(0);
    setFormError("");
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setEditingSlot(null);
    setFormData(emptySlot);
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");

    if (!formData.offering_id || !formData.instructor_id) {
      setFormError("Course offering and instructor are required.");
      setSaving(false);
      return;
    }
    if (durationOf(formData.start_time, formData.end_time) <= 0) {
      setFormError("End time must be after start time.");
      setSaving(false);
      return;
    }

    const payload = {
      offering_id: Number(formData.offering_id),
      primary_instructor_id: Number(formData.instructor_id),
      ta_instructor_id: null,
      day_of_week: Number(formData.day_of_week),
      start_time: formData.start_time,
      end_time: formData.end_time,
    };

    try {
      if (editingSlot) {
        await api.put(
          `/timetable/slots/${editingSlot.slot_id}`,
          payload,
          { params: { semester_id: semesterId, hall_id: hallId } },
        );
        setSuccessMessage("Timetable slot updated successfully.");
      } else {
        await api.post("/timetable/slots", {
          ...payload,
          semester_id: Number(semesterId),
          hall_id: Number(hallId),
        });
        setSuccessMessage("Timetable slot created successfully.");
      }
      closeModal();
      await loadSlots();
    } catch (error) {
      setFormError(getErrorDetail(error, "Unable to save timetable slot."));
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteSlot) return;
    setSaving(true);
    setPageError("");
    try {
      await api.delete(`/timetable/slots/${deleteSlot.slot_id}`);
      setSuccessMessage("Timetable slot removed successfully.");
      setDeleteSlot(null);
      await loadSlots();
    } catch (error) {
      setPageError(getErrorDetail(error, "Unable to remove timetable slot."));
    } finally {
      setSaving(false);
    }
  };

  const selectedHall = halls.find((hall) => String(hall.hall_id) === hallId);
  const duration = durationOf(formData.start_time, formData.end_time);

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Hall Schedule Management</h1>
            <p className="text-muted">Manage weekly timetable slots for lecture halls.</p>
          </div>
        </div>

        {successMessage && <div className="alert alert--success"><div className="alert__body">{successMessage}</div></div>}
        {pageError && <div className="alert alert--error"><div className="alert__body">{pageError}</div></div>}

        <section className="section">
          <div className="toolbar timetable-toolbar">
            <label className="form-field">
              <span>Semester</span>
              <select className="select" value={semesterId} onChange={(event) => setSemesterId(event.target.value)}>
                <option value="">Select semester</option>
                {semesters.map((semester) => (
                  <option key={semester.semester_id} value={semester.semester_id}>{semester.semester_name}</option>
                ))}
              </select>
            </label>
            <label className="form-field">
              <span>Lecture Hall</span>
              <select className="select" value={hallId} onChange={(event) => setHallId(event.target.value)}>
                <option value="">Select hall</option>
                {halls.map((hall) => (
                  <option key={hall.hall_id} value={hall.hall_id}>{hall.hall_name} — {hall.building}</option>
                ))}
              </select>
            </label>
            <button type="button" className="btn btn--primary" onClick={() => openCreateModal()} disabled={!semesterId || !hallId}>
              <Plus size={18} /> Add Slot
            </button>
          </div>

          {!semesterId || !hallId ? (
            <div className="card"><div className="empty-state"><CalendarDays size={28} /><h3>Select a semester and lecture hall</h3></div></div>
          ) : (
            <div className="card timetable-card">
              <div className="timetable-card__header">
                <div>
                  <h2>{selectedHall?.hall_name || "Lecture Hall"}</h2>
                  <p className="text-muted text-sm">{selectedHall?.building} · Capacity {selectedHall?.capacity}</p>
                </div>
              </div>

              {loading ? (
                <div className="loading-state"><div className="spinner" /><p>Loading schedule...</p></div>
              ) : (
                <div className="timetable-grid" role="grid">
                  {days.map((day) => {
                    const daySlots = slots
                      .filter((slot) => slot.day_of_week === day.value)
                      .sort((a, b) => a.start_time.localeCompare(b.start_time));

                    return (
                      <section className="timetable-day" key={day.value} aria-label={day.label}>
                        <div className="timetable-day__header">
                          <strong>{day.label}</strong>
                          <button type="button" className="btn btn--ghost btn--icon btn--sm" title={`Add ${day.label} slot`} onClick={() => openCreateModal(day.value)}><Plus size={16} /></button>
                        </div>
                        <div className="timetable-day__body">
                          {daySlots.length === 0 ? (
                            <button type="button" className="timetable-empty" onClick={() => openCreateModal(day.value)}>
                              <Plus size={16} /> Available
                            </button>
                          ) : daySlots.map((slot) => (
                            <article className="timetable-slot" key={slot.slot_id}>
                              <div className="timetable-slot__time">
                                <Clock3 size={14} />
                                {slot.start_time}–{slot.end_time}
                                <span>{formatDuration(slot.duration_minutes)}</span>
                              </div>
                              <h3>{slot.course_code}</h3>
                              <p>{slot.course_name}</p>
                              <p className="text-sm">Lecturer: {slot.lecturer_name}</p>
                              {slot.ta_name && <p className="text-sm">TA: {slot.ta_name}</p>}
                              <div className="timetable-slot__actions">
                                <button type="button" className="btn btn--ghost btn--icon btn--sm" title="Edit slot" onClick={() => openEditModal(slot)}><Pencil size={15} /></button>
                                <button type="button" className="btn btn--danger-ghost btn--icon btn--sm" title="Remove slot" onClick={() => setDeleteSlot(slot)}><Trash2 size={15} /></button>
                              </div>
                            </article>
                          ))}
                        </div>
                      </section>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {modalOpen && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeModal();
        }}>
          <div className="modal modal--lg" role="dialog" aria-modal="true">
            <form onSubmit={handleSubmit}>
              <div className="modal__header">
                <div>
                  <h2 className="modal__title">{editingSlot ? "Edit Timetable Slot" : "Add Timetable Slot"}</h2>
                  <p className="text-sm text-muted">{selectedHall?.hall_name} · {selectedHall?.building}</p>
                </div>
                <button type="button" className="btn btn--ghost btn--icon" onClick={closeModal}><X size={18} /></button>
              </div>
              <div className="modal__body">
                {formError && <div className="alert alert--error"><div className="alert__body">{formError}</div></div>}
                <div className="form-grid timetable-form-grid">
                  <label className="form-field">
                    <span>Day</span>
                    <select className="select" value={formData.day_of_week} onChange={(event) => setFormData({ ...formData, day_of_week: event.target.value })}>
                      {days.map((day) => <option key={day.value} value={day.value}>{day.label}</option>)}
                    </select>
                  </label>

                  <label className="form-field">
                    <span>Start Time</span>
                    <input type="time" className="input" value={formData.start_time} onChange={(event) => setFormData({ ...formData, start_time: event.target.value })} required />
                  </label>

                  <label className="form-field">
                    <span>End Time</span>
                    <input type="time" className="input" value={formData.end_time} onChange={(event) => setFormData({ ...formData, end_time: event.target.value })} required />
                  </label>

                  <div className="form-field">
                    <span>Duration</span>
                    <div className="input timetable-duration">{duration > 0 ? formatDuration(duration) : "Invalid time"}</div>
                  </div>

                  <label className="form-field timetable-form-grid__wide">
                    <span>Course Offering</span>
                    <div className="search">
                      <Search size={18} className="search__icon" />
                      <input
                        className="input"
                        type="text"
                        role="searchbox"
                        placeholder="Search course offerings..."
                        value={offeringSearch}
                        onChange={(event) => {
                          setOfferingSearch(event.target.value);
                          setOfferingOffset(0);
                        }}
                      />
                    </div>
                    <select className="select" value={formData.offering_id} onChange={(event) => setFormData({ ...formData, offering_id: event.target.value, instructor_id: "" })} required>
                      <option value="">Select course offering</option>
                      {offerings.map((offering) => (
                        <option key={offering.offering_id} value={offering.offering_id}>{offering.course_code} — {offering.course_name}</option>
                      ))}
                    </select>
                    <div className="cluster cluster--between">
                      <span className="text-sm text-muted">{offeringTotal} offerings</span>
                      <div className="action-group">
                        <button type="button" className="btn btn--secondary btn--sm" disabled={offeringOffset === 0} onClick={() => setOfferingOffset((previous) => Math.max(0, previous - offeringLimit))}>Previous</button>
                        <button type="button" className="btn btn--secondary btn--sm" disabled={offeringOffset + offeringLimit >= offeringTotal} onClick={() => setOfferingOffset((previous) => previous + offeringLimit)}>Next</button>
                      </div>
                    </div>
                  </label>

                  <label className="form-field">
                    <span>Instructor Type</span>
                    <select className="select" value={formData.instructor_role} onChange={(event) => setFormData({ ...formData, instructor_role: event.target.value, instructor_id: "" })}>
                      <option value="Lecturer">Lecturer</option>
                      <option value="TA">Teaching Assistant</option>
                    </select>
                  </label>

                  <label className="form-field">
                    <span>{formData.instructor_role === "TA" ? "Teaching Assistant" : "Lecturer"}</span>
                    <select className="select" value={formData.instructor_id} onChange={(event) => setFormData({ ...formData, instructor_id: event.target.value })} required>
                      <option value="">Select instructor</option>
                      {(formData.instructor_role === "TA" ? tas : lecturers).map((instructor) => <option key={instructor.instructor_id} value={instructor.instructor_id}>{instructor.full_name}</option>)}
                    </select>
                  </label>
                </div>
              </div>
              <div className="modal__footer">
                <button type="button" className="btn btn--secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={saving || duration <= 0}>{saving ? "Saving..." : editingSlot ? "Save Changes" : "Create Slot"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteSlot && (
        <div className="modal-backdrop"><div className="modal modal--sm" role="alertdialog" aria-modal="true">
          <div className="modal__header"><h2 className="modal__title">Remove Timetable Slot</h2><button type="button" className="btn btn--ghost btn--icon" onClick={() => setDeleteSlot(null)}><X size={18} /></button></div>
          <div className="modal__body"><p>Remove <strong>{deleteSlot.course_code}</strong> from {days.find((day) => day.value === deleteSlot.day_of_week)?.label} at {deleteSlot.start_time}?</p></div>
          <div className="modal__footer"><button type="button" className="btn btn--secondary" onClick={() => setDeleteSlot(null)}>Cancel</button><button type="button" className="btn btn--danger" onClick={confirmDelete} disabled={saving}>{saving ? "Removing..." : "Remove Slot"}</button></div>
        </div></div>
      )}
    </div>
  );
}
