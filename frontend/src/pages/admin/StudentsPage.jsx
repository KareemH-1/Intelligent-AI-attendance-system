import { useCallback, useEffect, useState } from "react";
import { Plus, Search, Pencil, Trash2, Users, X, Camera } from "lucide-react";

import api from "../../services/api";
import FaceRegistrationStep from "../../components/FaceRegistrationStep";

const emptyForm = {
  university_id: "",
  full_name: "",
  email: "",
  department: "",
  academic_year: "1",
};

export default function StudentsPage() {
  const [students, setStudents] = useState([]);
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [formError, setFormError] = useState("");
  const [registrationStep, setRegistrationStep] = useState(1);
  const [createdStudent, setCreatedStudent] = useState(null);

  const [universityIdLoading, setUniversityIdLoading] = useState(false);
  const [universityIdError, setUniversityIdError] = useState("");

  const numberFormatter = new Intl.NumberFormat();

  const loadStudents = useCallback(async (searchValue = "", signal) => {
    try {
      setLoading(true);
      setPageError("");

      const response = await api.get("/students", {
        params: {
          search: searchValue,
        },
        signal,
      });

      setStudents(response.data);
    } catch (error) {
      if (signal && signal.aborted) {
        return;
      }

      setPageError(
        error.response?.data?.detail ||
          "Failed to load students. Please try again.",
      );
    } finally {
      if (!signal || !signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
      loadStudents(search, controller.signal);
    }, 300);

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [search, loadStudents]);

  useEffect(() => {
    if (!modalOpen || editingStudent) {
      return;
    }

    const controller = new AbortController();

    const fetchNextUniversityId = async () => {
      setUniversityIdLoading(true);
      setUniversityIdError("");

      try {
        const response = await api.get("/students/next-university-id", {
          signal: controller.signal,
        });

        setFormData((previous) => ({
          ...previous,
          university_id: response.data.university_id,
        }));
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setUniversityIdError(
          error.response?.data?.detail ||
            "Could not generate a suggested ID. You can enter one manually.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setUniversityIdLoading(false);
        }
      }
    };

    fetchNextUniversityId();

    return () => {
      controller.abort();
    };
  }, [modalOpen, editingStudent]);
  const openCreateModal = () => {
    setEditingStudent(null);
    setCreatedStudent(null);
    setRegistrationStep(1);
    setFormData({ ...emptyForm });
    setFormError("");
    setUniversityIdError("");
    setModalOpen(true);
  };
  const openEditModal = (student) => {
    setEditingStudent(student);
    setCreatedStudent(null);
    setRegistrationStep(1);

    setFormData({
      university_id: student.university_id,
      full_name: student.full_name,
      email: student.email || "",
      department: student.department,
      academic_year: String(student.academic_year),
    });

    setFormError("");
    setUniversityIdError("");
    setModalOpen(true);
  };
  const closeModal = () => {
    if (saving) {
      return;
    }

    setModalOpen(false);
    setEditingStudent(null);
    setCreatedStudent(null);
    setRegistrationStep(1);
    setFormData({ ...emptyForm });
    setFormError("");
  };
  const handleInputChange = (event) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };
  const handleSubmit = async (event) => {
    event.preventDefault();

    setSaving(true);
    setFormError("");
    setSuccessMessage("");

    const payload = {
      university_id: formData.university_id.trim(),
      full_name: formData.full_name.trim(),
      email: formData.email.trim() || null,
      department: formData.department.trim(),
      academic_year: Number(formData.academic_year),
    };

    try {
      if (editingStudent) {
        await api.put(`/students/${editingStudent.student_id}`, payload);

        setCreatedStudent({
          person_id: editingStudent.person_id,
          full_name: payload.full_name,
        });

        setRegistrationStep(2);
        setSuccessMessage("Student information updated successfully.");

        await loadStudents(search);
        return;
      }

      const response = await api.post("/students", payload);

      const student = {
        student_id: response.data.student_id,
        person_id: response.data.person_id,
        full_name: payload.full_name,
        university_id: payload.university_id,
      };

      if (!student.student_id || !student.person_id) {
        setFormError(
          "Student was created, but the server did not return the required IDs for face registration. Please refresh the student list.",
        );

        await loadStudents(search);
        return;
      }

      setCreatedStudent(student);
      setRegistrationStep(2);

      await loadStudents(search);
    } catch (error) {
      setFormError(
        error.response?.data?.detail || "Unable to save student information.",
      );
    } finally {
      setSaving(false);
    }
  };

  const handleStartFaceReregistration = () => {
    if (!editingStudent?.person_id) {
      setFormError(
        "Unable to start face registration because the student's person ID is unavailable.",
      );
      return;
    }

    setCreatedStudent({
      person_id: editingStudent.person_id,
      full_name: formData.full_name.trim(),
    });

    setFormError("");
    setRegistrationStep(2);
  };
  const handleDelete = async (student) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${student.full_name}?`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingId(student.student_id);
    setPageError("");
    setSuccessMessage("");

    try {
      await api.delete(`/students/${student.student_id}`);

      setSuccessMessage("Student deleted successfully.");

      await loadStudents(search);
    } catch (error) {
      setPageError(
        error.response?.data?.detail || "Unable to delete this student.",
      );
    } finally {
      setDeletingId(null);
    }
  };
  const handleFaceRegistrationComplete = async () => {
    setSuccessMessage(
      editingStudent
        ? "Student face registration updated successfully."
        : "Student and face registration completed successfully.",
    );

    setModalOpen(false);
    setEditingStudent(null);
    setCreatedStudent(null);
    setRegistrationStep(1);
    setFormData({ ...emptyForm });

    await loadStudents(search);
  };

  const handleSkipFaceRegistration = async () => {
    setSuccessMessage(
      editingStudent
        ? "Face registration was not changed."
        : "Student registered successfully. Face registration can be completed later.",
    );

    setModalOpen(false);
    setEditingStudent(null);
    setCreatedStudent(null);
    setRegistrationStep(1);
    setFormData({ ...emptyForm });

    await loadStudents(search);
  };
  return (
    <div className="page students-page">
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Students</h1>
            <p className="text-muted">
              Register and manage university students.
            </p>
          </div>

          <button
            type="button"
            className="btn btn--primary"
            onClick={openCreateModal}
          >
            <Plus size={18} />
            Add Student
          </button>
        </div>

        {successMessage && (
          <div
            className="alert alert--success"
            role="status"
            aria-live="polite"
          >
            <div className="alert__body">{successMessage}</div>
          </div>
        )}

        {pageError && (
          <div className="alert alert--error" role="alert" aria-live="polite">
            <div className="alert__body">{pageError}</div>
          </div>
        )}

        <section className="section">
          <div className="toolbar">
            <div className="search students-search">
              <Search className="search__icon" size={18} aria-hidden="true" />

              <label htmlFor="student-search" className="sr-only">
                Search students
              </label>

              <input
                id="student-search"
                type="search"
                className="input"
                placeholder="Search by name, university ID, email or faculty..."
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                }}
              />
            </div>

            <div className="text-muted text-sm">
              {numberFormatter.format(students.length)} students
            </div>
          </div>

          <div className="card students-table-card">
            <div className="table-wrap students-table-wrap">
              <table className="table students-table">
                <thead>
                  <tr>
                    <th className="students-table__id">University ID</th>
                    <th className="students-table__name">Student Name</th>
                    <th className="students-table__email">Email</th>
                    <th className="students-table__faculty">Faculty</th>
                    <th className="students-table__year">Academic Year</th>
                    <th className="students-table__actions">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {loading && (
                    <tr>
                      <td colSpan="6">
                        <div className="loading-state">
                          <div className="spinner" />
                          <p>Loading students...</p>
                        </div>
                      </td>
                    </tr>
                  )}

                  {!loading && students.length === 0 && (
                    <tr>
                      <td colSpan="6">
                        <div className="empty-state">
                          <div className="empty-state__icon">
                            <Users size={28} />
                          </div>

                          <h3 className="empty-state__title">
                            No students found
                          </h3>

                          <p className="empty-state__text">
                            {search
                              ? "Try changing your search."
                              : "Register your first student to get started."}
                          </p>

                          {!search && (
                            <button
                              type="button"
                              className="btn btn--primary"
                              onClick={openCreateModal}
                            >
                              <Plus size={16} />
                              Add Student
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}

                  {!loading &&
                    students.map((student) => (
                      <tr key={student.student_id}>
                        <td className="students-table__id">
                          <span className="mono font-medium">
                            {student.university_id}
                          </span>
                        </td>

                        <td className="students-table__name">
                          <span className="font-medium">
                            {student.full_name}
                          </span>
                        </td>

                        <td className="students-table__email">
                          {student.email || (
                            <span className="text-muted">Not provided</span>
                          )}
                        </td>

                        <td className="students-table__faculty">
                          {student.department || "—"}
                        </td>

                        <td className="students-table__year">
                          Year {student.academic_year}
                        </td>

                        <td className="students-table__actions">
                          <div className="cell-actions">
                            <button
                              type="button"
                              className="btn btn--ghost btn--icon"
                              aria-label={`Edit ${student.full_name}`}
                              title="Edit student"
                              onClick={() => {
                                openEditModal(student);
                              }}
                            >
                              <Pencil size={16} />
                            </button>

                            <button
                              type="button"
                              className="btn btn--danger-ghost btn--icon"
                              aria-label={`Delete ${student.full_name}`}
                              title="Delete student"
                              disabled={deletingId === student.student_id}
                              onClick={() => {
                                handleDelete(student);
                              }}
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {modalOpen && (
          <div
            className="modal-backdrop"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) {
                closeModal();
              }
            }}
          >
            <div
              className="modal modal--lg"
              role="dialog"
              aria-modal="true"
              aria-labelledby="student-modal-title"
            >
              <div className="modal__header">
                <div>
                  <h2 id="student-modal-title">
                    {registrationStep === 2
                      ? "Face Registration"
                      : editingStudent
                        ? "Edit Student"
                        : "Register Student"}
                  </h2>

                  <p className="text-muted text-sm">
                    {registrationStep === 2
                      ? "Step 2 of 2 — Capture or replace the student's face data."
                      : editingStudent
                        ? "Update the student's university information."
                        : "Step 1 of 2 — Enter the student's university information."}
                  </p>
                </div>

                <button
                  type="button"
                  className="btn btn--ghost btn--icon"
                  aria-label="Close modal"
                  onClick={closeModal}
                  disabled={saving}
                >
                  <X size={20} />
                </button>
              </div>

              {registrationStep === 1 ? (
                <form onSubmit={handleSubmit}>
                  <div className="modal__body">
                    {formError && (
                      <div className="alert alert--error" role="alert">
                        <div className="alert__body">{formError}</div>
                      </div>
                    )}

                    <div className="stack gap-4">
                      <div className="form-group">
                        <label
                          htmlFor="university_id"
                          className="label label--required"
                        >
                          University ID
                        </label>

                        <input
                          id="university_id"
                          name="university_id"
                          type="text"
                          className="input"
                          placeholder={
                            universityIdLoading
                              ? "Generating University ID..."
                              : "Enter university ID..."
                          }
                          value={formData.university_id}
                          onChange={handleInputChange}
                          maxLength={30}
                          required
                          disabled={universityIdLoading}
                        />

                        {universityIdLoading && (
                          <p className="form-hint" aria-live="polite">
                            Generating the next available University ID...
                          </p>
                        )}

                        {universityIdError && (
                          <p className="form-error" role="alert">
                            {universityIdError}
                          </p>
                        )}
                      </div>

                      <div className="form-group">
                        <label
                          htmlFor="full_name"
                          className="label label--required"
                        >
                          Full Name
                        </label>

                        <input
                          id="full_name"
                          name="full_name"
                          type="text"
                          className="input"
                          placeholder="Enter full name..."
                          value={formData.full_name}
                          onChange={handleInputChange}
                          maxLength={150}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label htmlFor="email" className="label">
                          Email Address
                        </label>

                        <input
                          id="email"
                          name="email"
                          type="email"
                          className="input"
                          placeholder="Enter email address..."
                          value={formData.email}
                          onChange={handleInputChange}
                          maxLength={150}
                        />
                      </div>

                      <div className="form-group">
                        <label
                          htmlFor="department"
                          className="label label--required"
                        >
                          Faculty
                        </label>

                        <input
                          id="department"
                          name="department"
                          type="text"
                          className="input"
                          placeholder="Enter faculty..."
                          value={formData.department}
                          onChange={handleInputChange}
                          maxLength={100}
                          required
                        />
                      </div>

                      <div className="form-group">
                        <label
                          htmlFor="academic_year"
                          className="label label--required"
                        >
                          Academic Year
                        </label>

                        <select
                          id="academic_year"
                          name="academic_year"
                          className="select"
                          value={formData.academic_year}
                          onChange={handleInputChange}
                          required
                        >
                          <option value="1">First Year</option>
                          <option value="2">Second Year</option>
                          <option value="3">Third Year</option>
                          <option value="4">Fourth Year</option>
                          <option value="5">Fifth Year</option>
                          <option value="6">Sixth Year</option>
                          <option value="7">Seventh Year</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="modal__footer">
                    <button
                      type="button"
                      className="btn btn--secondary"
                      onClick={closeModal}
                      disabled={saving}
                    >
                      Cancel
                    </button>

                    {editingStudent && (
                      <button
                        type="button"
                        className="btn btn--secondary"
                        onClick={handleStartFaceReregistration}
                        disabled={saving}
                      >
                        <Camera size={16} />
                        Change Face Registration
                      </button>
                    )}

                    <button
                      type="submit"
                      className="btn btn--primary"
                      disabled={saving || universityIdLoading}
                    >
                      {saving
                        ? "Saving..."
                        : editingStudent
                          ? "Save Changes"
                          : "Continue to Face Registration"}
                    </button>
                  </div>
                </form>
              ) : (
                <FaceRegistrationStep
                  personId={createdStudent.person_id}
                  studentName={createdStudent.full_name}
                  onComplete={handleFaceRegistrationComplete}
                  onSkip={handleSkipFaceRegistration}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
