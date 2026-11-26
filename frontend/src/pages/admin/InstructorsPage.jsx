import { useCallback, useEffect, useState } from "react";
import { Plus, Search, Pencil, Eye, Camera, Power, BookOpen, Trash2, X, Users } from "lucide-react";

import api from "../../services/api";
import FaceRegistrationStep from "../../components/FaceRegistrationStep";

const emptyForm = {
  university_id: "",
  full_name: "",
  email: "",
  department: "",
  instructor_type: "Lecturer",
  username: "",
  password: "",
};

function getErrorDetail(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message)
      .filter(Boolean)
      .join(" ");
  }
  return fallback;
}

export default function InstructorsPage() {
  const [instructors, setInstructors] = useState([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingInstructor, setEditingInstructor] = useState(null);
  const [viewInstructor, setViewInstructor] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [formError, setFormError] = useState("");
  const [registrationStep, setRegistrationStep] = useState(1);
  const [createdInstructor, setCreatedInstructor] = useState(null);
  const [assignmentInstructor, setAssignmentInstructor] = useState(null);
  const [semesters, setSemesters] = useState([]);
  const [semesterId, setSemesterId] = useState("");
  const [offerings, setOfferings] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [offeringId, setOfferingId] = useState("");
  const [assignmentLoading, setAssignmentLoading] = useState(false);
  const [assignmentSearch, setAssignmentSearch] = useState("");
  const [assignmentOffset, setAssignmentOffset] = useState(0);
  const [assignmentTotal, setAssignmentTotal] = useState(0);
  const assignmentLimit = 20;

  const loadInstructors = useCallback(async (searchValue = "", type = "", signal) => {
    try {
      setLoading(true);
      setPageError("");
      const response = await api.get("/instructors", {
        params: { search: searchValue, instructor_type: type },
        signal,
      });
      setInstructors(response.data);
    } catch (error) {
      if (!signal?.aborted) {
        setPageError(getErrorDetail(error, "Failed to load instructors."));
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [assignmentSearch, assignmentOffset]);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      loadInstructors(search, typeFilter, controller.signal);
    }, 300);
    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [search, typeFilter, loadInstructors]);

  useEffect(() => {
    api.get("/semesters").then((response) => {
      setSemesters(response.data);
      const active = response.data.find((semester) => semester.is_active);
      if (active) setSemesterId(String(active.semester_id));
    }).catch((error) => {
      setPageError(getErrorDetail(error, "Failed to load semesters."));
    });
  }, []);

  const openCreateModal = async () => {
    setEditingInstructor(null);
    setCreatedInstructor(null);
    setRegistrationStep(1);
    setFormData(emptyForm);
    setFormError("");
    setModalOpen(true);
    try {
      const response = await api.get("/instructors/next-university-id");
      setFormData((previous) => ({ ...previous, university_id: response.data.university_id }));
    } catch {
      // The suggested ID is optional; the field remains editable.
    }
  };

  const openEditModal = (instructor) => {
    setEditingInstructor(instructor);
    setCreatedInstructor(null);
    setRegistrationStep(1);
    setFormData({
      university_id: instructor.university_id,
      full_name: instructor.full_name,
      email: instructor.email || "",
      department: instructor.department,
      instructor_type: instructor.instructor_type,
      username: instructor.username,
      password: "",
    });
    setFormError("");
    setModalOpen(true);
  };

  const openFaceRegistration = (instructor) => {
    setEditingInstructor(instructor);
    setCreatedInstructor({
      person_id: instructor.person_id,
      full_name: instructor.full_name,
    });
    setFormError("");
    setRegistrationStep(2);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setEditingInstructor(null);
    setCreatedInstructor(null);
    setRegistrationStep(1);
    setFormData(emptyForm);
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");

    if (editingInstructor && formData.password && formData.password.length < 8) {
      setFormError("Temporary password must contain at least 8 characters.");
      setSaving(false);
      return;
    }

    if (formData.full_name.trim().length === 0 ||
        formData.email.trim().length === 0 ||
        formData.department.trim().length === 0 ||
        formData.university_id.trim().length === 0 ||
        (!editingInstructor && formData.username.trim().length === 0)) {
      setFormError("Please complete all required instructor fields.");
      setSaving(false);
      return;
    }
    const payload = {
      university_id: formData.university_id.trim(),
      full_name: formData.full_name.trim(),
      email: formData.email.trim(),
      department: formData.department.trim(),
      instructor_type: formData.instructor_type,
      username: formData.username.trim(),
    };
    if (editingInstructor && formData.password) {
      payload.password = formData.password;
    }

    try {
      if (editingInstructor) {
        await api.put(`/instructors/${editingInstructor.instructor_id}`, payload);
        setCreatedInstructor({ person_id: editingInstructor.person_id, full_name: payload.full_name });
        setRegistrationStep(2);
        setSuccessMessage("Instructor information updated successfully.");
      } else {
        const response = await api.post("/instructors", payload);
        setCreatedInstructor({
          instructor_id: response.data.instructor_id,
          person_id: response.data.person_id,
          full_name: payload.full_name,
        });
        setRegistrationStep(2);
      }
      await loadInstructors(search, typeFilter);
    } catch (error) {
      setFormError(getErrorDetail(error, "Unable to save instructor."));
    } finally {
      setSaving(false);
    }
  };

  const toggleAccount = async (instructor) => {
    setPageError("");
    setSuccessMessage("");
    try {
      const response = await api.patch(`/instructors/${instructor.instructor_id}/account-status`, {
        is_active: !instructor.is_active,
      });
      setSuccessMessage(response.data.message);
      await loadInstructors(search, typeFilter);
    } catch (error) {
      setPageError(getErrorDetail(error, "Unable to change account status."));
    }
  };

  const loadAssignmentData = useCallback(async (instructorId, selectedSemester) => {
    if (!selectedSemester) return;
    setAssignmentLoading(true);
    setPageError("");
    try {
      const [offeringsResponse, assignmentsResponse] = await Promise.all([
        api.get(`/instructors/offerings/semesters/${selectedSemester}`, {
          params: {
            search: assignmentSearch,
            limit: assignmentLimit,
            offset: assignmentOffset,
            instructor_id: instructorId,
          },
        }),
        api.get(`/instructors/${instructorId}/offerings`, { params: { semester_id: selectedSemester } }),
      ]);
      setOfferings(offeringsResponse.data.items);
      setAssignmentTotal(offeringsResponse.data.total);
      setAssignments(assignmentsResponse.data);
    } catch (error) {
      setPageError(getErrorDetail(error, "Failed to load course assignments."));
    } finally {
      setAssignmentLoading(false);
    }
  }, []);

  const openAssignments = (instructor) => {
    setAssignmentInstructor(instructor);
    setOfferingId("");
    setAssignmentSearch("");
    setAssignmentOffset(0);
  };

  useEffect(() => {
    if (assignmentInstructor && semesterId) {
      const timeoutId = setTimeout(() => {
        loadAssignmentData(
          assignmentInstructor.instructor_id,
          semesterId,
        );
      }, 300);

      return () => clearTimeout(timeoutId);
    }
  }, [
    semesterId,
    assignmentInstructor,
    assignmentSearch,
    assignmentOffset,
    loadAssignmentData,
  ]);

  const addAssignment = async (selectedOfferingId = offeringId) => {
    if (!selectedOfferingId) return;
    setAssignmentLoading(true);
    setPageError("");
    try {
      await api.post("/instructors/offerings", {
        instructor_id: assignmentInstructor.instructor_id,
        offering_id: Number(selectedOfferingId),
        instructor_role: assignmentInstructor.instructor_type,
      });
      setSuccessMessage("Instructor assigned successfully.");
      setOfferingId("");
      await loadAssignmentData(assignmentInstructor.instructor_id, semesterId);
    } catch (error) {
      setPageError(getErrorDetail(error, "Unable to add assignment."));
    } finally {
      setAssignmentLoading(false);
    }
  };

  const removeAssignment = async (assignment) => {
    setAssignmentLoading(true);
    setPageError("");
    try {
      await api.delete(`/instructors/offerings/${assignment.instructor_offering_id}`);
      setSuccessMessage("Instructor assignment removed successfully.");
      await loadAssignmentData(assignmentInstructor.instructor_id, semesterId);
    } catch (error) {
      setPageError(getErrorDetail(error, "Unable to remove assignment."));
    } finally {
      setAssignmentLoading(false);
    }
  };

  const faceComplete = async () => {
    setSuccessMessage("Instructor face registration saved successfully.");
    closeModal();
    await loadInstructors(search, typeFilter);
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <div><h1>Instructors</h1><p className="text-muted">Register lecturers and teaching assistants.</p></div>
          <button type="button" className="btn btn--primary" onClick={openCreateModal}><Plus size={18} /> Add Instructor</button>
        </div>
        {successMessage && <div className="alert alert--success" role="status"><div className="alert__body">{successMessage}</div></div>}
        {pageError && <div className="alert alert--error" role="alert"><div className="alert__body">{pageError}</div></div>}
        <section className="section">
          <div className="toolbar">
            <div className="search instructors-search">
              <Search className="search__icon" size={18} />
              <input className="input" type="text" role="searchbox" placeholder="Search instructors..." value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <select className="select" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} aria-label="Filter by instructor type">
              <option value="">All instructor types</option>
              <option value="Lecturer">Lecturers</option>
              <option value="TA">Teaching Assistants</option>
            </select>
          </div>
          <div className="card"><div className="table-wrap"><table className="table">
            <thead><tr><th>University ID</th><th>Name</th><th>Type</th><th>Department</th><th>Face</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {loading && <tr><td colSpan="7"><div className="loading-state"><div className="spinner" /><p>Loading instructors...</p></div></td></tr>}
              {!loading && instructors.length === 0 && <tr><td colSpan="7"><div className="empty-state"><Users size={28} /><h3>No instructors found</h3></div></td></tr>}
              {!loading && instructors.map((instructor) => (
                <tr key={instructor.instructor_id}>
                  <td className="mono font-medium">{instructor.university_id}</td>
                  <td><div className="font-medium">{instructor.full_name}</div><div className="text-muted text-sm">{instructor.email}</div></td>
                  <td>{instructor.instructor_type}</td><td>{instructor.department}</td>
                  <td>{instructor.has_face_registration ? "Registered" : "Not registered"}</td>
                  <td>{instructor.is_active ? "Active" : "Inactive"}</td>
                  <td><div className="cell-actions">
                    <button type="button" className="btn btn--ghost btn--icon" title="View" onClick={() => setViewInstructor(instructor)}><Eye size={16} /></button>
                    <button type="button" className="btn btn--ghost btn--icon" title="Edit" onClick={() => openEditModal(instructor)}><Pencil size={16} /></button>
                    <button type="button" className="btn btn--ghost btn--icon" title="Face registration" onClick={() => openFaceRegistration(instructor)}><Camera size={16} /></button>
                    <button type="button" className="btn btn--ghost btn--icon" title="Course assignments" onClick={() => openAssignments(instructor)}><BookOpen size={16} /></button>
                    <button type="button" className="btn btn--ghost btn--icon" title={instructor.is_active ? "Deactivate" : "Activate"} onClick={() => toggleAccount(instructor)}><Power size={16} /></button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table></div></div>
        </section>
      </div>

      {modalOpen && (
        <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) closeModal(); }}>
          <div className="modal modal--lg" role="dialog" aria-modal="true">
            {registrationStep === 1 ? (
              <form onSubmit={handleSubmit}>
                <div className="modal__header"><h2 className="modal__title">{editingInstructor ? "Edit Instructor" : "Add Instructor"}</h2><button type="button" className="btn btn--ghost btn--icon" onClick={closeModal}><X size={18} /></button></div>
                <div className="modal__body">
                  {formError && <div className="alert alert--error"><div className="alert__body">{formError}</div></div>}
                  <div className="form-grid">
                    <label className="form-field"><span>University ID</span><input className="input" value={formData.university_id} onChange={(e) => setFormData({...formData, university_id: e.target.value})} required /></label>
                    <label className="form-field"><span>Full name</span><input className="input" value={formData.full_name} onChange={(e) => setFormData({...formData, full_name: e.target.value})} required /></label>
                    <label className="form-field"><span>Email</span><input className="input" type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} required /></label>
                    <label className="form-field"><span>Department</span><input className="input" value={formData.department} onChange={(e) => setFormData({...formData, department: e.target.value})} required /></label>
                    <label className="form-field"><span>Instructor type</span><select className="select" value={formData.instructor_type} onChange={(e) => setFormData({...formData, instructor_type: e.target.value})}><option value="Lecturer">Lecturer</option><option value="TA">Teaching Assistant</option></select></label>
                    <label className="form-field"><span>Username</span><input className="input" value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} required={!editingInstructor} /></label>
                    {!editingInstructor && <p className="form-hint">The account starts with the system temporary password and must change it at first login.</p>}
                    {editingInstructor && <label className="form-field"><span>Temporary password (forces change at next login)</span><input className="input" type="password" minLength={8} value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} /></label>}
                  </div>
                </div>
                <div className="modal__footer"><button type="button" className="btn btn--secondary" onClick={closeModal}>Cancel</button><button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Saving..." : editingInstructor ? "Save & Continue" : "Create & Register Face"}</button></div>
              </form>
            ) : (
              <>
                <div className="modal__header"><h2 className="modal__title">Face Registration</h2><button type="button" className="btn btn--ghost btn--icon" onClick={closeModal}><X size={18} /></button></div>
                {createdInstructor?.person_id && <FaceRegistrationStep personId={createdInstructor.person_id} studentName={createdInstructor.full_name} subjectType="people" onComplete={faceComplete} onSkip={closeModal} />}
              </>
            )}
          </div>
        </div>
      )}

      {viewInstructor && (
        <div className="modal-backdrop"><div className="modal modal--sm" role="dialog" aria-modal="true">
          <div className="modal__header"><h2 className="modal__title">Instructor Details</h2><button type="button" className="btn btn--ghost btn--icon" onClick={() => setViewInstructor(null)}><X size={18} /></button></div>
          <div className="modal__body">
            <p><strong>{viewInstructor.full_name}</strong></p><p>University ID: {viewInstructor.university_id}</p><p>Email: {viewInstructor.email}</p><p>Department: {viewInstructor.department}</p><p>Type: {viewInstructor.instructor_type}</p><p>Username: {viewInstructor.username}</p><p>Face: {viewInstructor.has_face_registration ? "Registered" : "Not registered"}</p><p>Account: {viewInstructor.is_active ? "Active" : "Inactive"}</p>
          </div>
          <div className="modal__footer"><button type="button" className="btn btn--secondary" onClick={() => setViewInstructor(null)}>Close</button></div>
        </div></div>
      )}

      {assignmentInstructor && (
        <div className="modal-backdrop"><div className="modal modal--lg" role="dialog" aria-modal="true">
          <div className="modal__header"><h2 className="modal__title">Course Assignments — {assignmentInstructor.full_name}</h2><button type="button" className="btn btn--ghost btn--icon" onClick={() => setAssignmentInstructor(null)}><X size={18} /></button></div>
          <div className="modal__body">
            <div className="toolbar">
              <label className="form-field"><span>Semester</span><select className="select" value={semesterId} onChange={(e) => { setSemesterId(e.target.value); setAssignmentSearch(""); setAssignmentOffset(0); }}><option value="">Select semester</option>{semesters.map((s) => <option key={s.semester_id} value={s.semester_id}>{s.semester_name}</option>)}</select></label>
            </div>

            <div className="toolbar">
              <div className="search">
                <Search size={18} className="search__icon" />
                <input
                  className="input"
                  type="text"
                  role="searchbox"
                  placeholder="Search available course offerings..."
                  value={assignmentSearch}
                  onChange={(event) => {
                    setAssignmentSearch(event.target.value);
                    setAssignmentOffset(0);
                  }}
                />
              </div>
              <span className="text-sm text-muted">
                {assignmentTotal} available course
                {assignmentTotal === 1 ? "" : "s"}
              </span>
            </div>

            {assignmentLoading ? (
              <div className="loading-state"><div className="spinner" /></div>
            ) : (
              <>
                <div className="table-wrap" style={{ maxHeight: "14rem", overflowY: "auto", marginBottom: "1rem" }}>
                  <table className="table">
                    <thead><tr><th>Available Course</th><th>Action</th></tr></thead>
                    <tbody>
                      {offerings.map((offering) => (
                        <tr key={offering.offering_id}>
                          <td><span className="font-medium">{offering.course_code}</span> — {offering.course_name}</td>
                          <td>
                            <button
                              type="button"
                              className="btn btn--primary btn--sm"
                              onClick={() =>
                                addAssignment(offering.offering_id)
                              }
                              disabled={assignmentLoading}
                            >
                              <Plus size={15} /> Assign
                            </button>
                          </td>
                        </tr>
                      ))}
                      {offerings.length === 0 && (
                        <tr><td colSpan="2"><div className="empty-state"><p>No matching course offerings available.</p></div></td></tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="action-group action-group--end" style={{ marginBottom: "1rem" }}>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    disabled={assignmentOffset === 0}
                    onClick={() => setAssignmentOffset((previous) => Math.max(0, previous - assignmentLimit))}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary"
                    disabled={assignmentOffset + assignmentLimit >= assignmentTotal}
                    onClick={() => setAssignmentOffset((previous) => previous + assignmentLimit)}
                  >
                    Next
                  </button>
                </div>

                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Assigned Course</th><th>Role</th><th>Action</th></tr></thead>
                    <tbody>
                      {assignments.map((assignment) => (
                        <tr key={assignment.instructor_offering_id}>
                          <td><span className="font-medium">{assignment.course_code}</span> — {assignment.course_name}</td>
                          <td>{assignment.instructor_role}</td>
                          <td><button type="button" className="btn btn--danger-ghost btn--icon" title="Remove assignment" onClick={() => removeAssignment(assignment)}><Trash2 size={16} /></button></td>
                        </tr>
                      ))}
                      {assignments.length === 0 && (
                        <tr><td colSpan="3"><div className="empty-state"><p>No course assignments for this semester.</p></div></td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </div></div>
      )}
    </div>
  );
}
