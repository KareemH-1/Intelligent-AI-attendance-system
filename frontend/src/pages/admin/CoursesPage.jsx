import { useEffect, useState } from "react";
import {
  BookOpen,
  Plus,
  Search,
  Pencil,
  Trash2,
  X,
  Clock3,
} from "lucide-react";

import api from "../../services/api";

export default function CoursesPage() {
  const [courses, setCourses] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);

  const [deleteCourse, setDeleteCourse] = useState(null);

  const emptyForm = {
    course_code: "",
    course_name: "",
    credit_hours: 3,
  };

  const [formData, setFormData] = useState(emptyForm);
  const [formError, setFormError] = useState("");

 

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      loadCourses(search);
    }, 300);

    return () => {
      clearTimeout(timeoutId);
    };
  }, [search]);

  const loadCourses = async (searchValue = "") => {
    try {
      setLoading(true);
      setPageError("");

      const response = await api.get("/courses", {
        params: {
          search: searchValue,
        },
      });

      setCourses(response.data);
    } catch (error) {
      setPageError(error.response?.data?.detail || "Failed to load courses.");
    } finally {
      setLoading(false);
    }
  };


  function openCreateModal() {
    setEditingCourse(null);
    setFormData(emptyForm);
    setFormError("");
    setModalOpen(true);
  }

  function openEditModal(course) {
    setEditingCourse(course);

    setFormData({
      course_code: course.course_code,
      course_name: course.course_name,
      credit_hours: course.credit_hours,
    });

    setFormError("");
    setModalOpen(true);
  }

  function closeModal() {
    if (saving) return;

    setModalOpen(false);
    setEditingCourse(null);
    setFormData(emptyForm);
    setFormError("");
  }

  function handleInputChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: name === "credit_hours" ? value : value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setFormError("");
    setPageError("");
    setSuccessMessage("");

    const courseCode = formData.course_code.trim();
    const courseName = formData.course_name.trim();
    const creditHours = Number(formData.credit_hours);

    if (!courseCode || !courseName) {
      setFormError("Please complete all required fields.");
      return;
    }

    if (
      !Number.isInteger(creditHours) ||
      creditHours < 1 ||
      creditHours > 255
    ) {
      setFormError("Credit hours must be a positive whole number.");
      return;
    }

    setSaving(true);

    const payload = {
      course_code: courseCode,
      course_name: courseName,
      credit_hours: creditHours,
    };

    try {
      if (editingCourse) {
        const response = await api.put(
          `/courses/${editingCourse.course_id}`,
          payload,
        );

        setSuccessMessage(response.data.message);
      } else {
        const response = await api.post("/courses", payload);

        setSuccessMessage(response.data.message);
      }

      closeModal();
      await loadCourses();
    } catch (error) {
      setFormError(error.response?.data?.detail || "Unable to save course.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!deleteCourse) return;

    setSaving(true);
    setPageError("");
    setSuccessMessage("");

    try {
      const response = await api.delete(`/courses/${deleteCourse.course_id}`);

      setSuccessMessage(response.data.message);
      setDeleteCourse(null);

      await loadCourses();
    } catch (error) {
      setPageError(error.response?.data?.detail || "Unable to delete course.");

      setDeleteCourse(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="page">
      <div className="page-header">
        <div className="page-header__text">
          <h1 className="page-header__title">Courses</h1>

          <p className="page-header__subtitle">
            Manage the university's academic courses.
          </p>
        </div>

        <div className="page-header__actions">
          <button className="btn btn--primary" onClick={openCreateModal}>
            <Plus size={18} />
            Add Course
          </button>
        </div>
      </div>

      {pageError && (
        <div className="alert alert--error mt-4" role="alert">
          <div className="alert__body">{pageError}</div>
        </div>
      )}

      {successMessage && (
        <div className="alert alert--success mt-4" role="status">
          <div className="alert__body">{successMessage}</div>
        </div>
      )}

      <section className="section">
        <div className="section__header">
          <div>
            <h2 className="section__title">All Courses</h2>
            <p className="text-sm text-muted">
              {courses.length} courses registered
            </p>
          </div>
        </div>

        <div className="toolbar">
          <div className="search">
            <Search size={18} className="search__icon" />

            <input
              type="search"
              className="input"
              placeholder="Search by course code or name…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search courses"
            />
          </div>
        </div>

        <div className="card">
          {loading ? (
            <div className="loading-state">
              <span className="spinner spinner--lg" />
              <p>Loading courses...</p>
            </div>
          ) : courses.length === 0 ? (
            <div className="empty-state">
              <BookOpen
                style={{ padding: "0.5rem" }}
                size={32}
                className="empty-state__icon"
              />

              <h3 className="empty-state__title">No courses found</h3>

              <p className="empty-state__text">
                {search
                  ? "Try another search term."
                  : "Start by adding your first course."}
              </p>

              {!search && (
                <button className="btn btn--primary" onClick={openCreateModal}>
                  <Plus size={17} />
                  Add Course
                </button>
              )}
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Course Code</th>
                    <th>Course Name</th>
                    <th>Credit Hours</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {courses.map((course) => (
                    <tr key={course.course_id}>
                      <td>
                        <span className="font-semibold mono">
                          {course.course_code}
                        </span>
                      </td>

                      <td>
                        <span className="text-strong">
                          {course.course_name}
                        </span>
                      </td>

                      <td>
                        <span className="cluster cluster--center gap-2">
                          <Clock3 size={15} className="text-muted" />
                          {course.credit_hours}
                        </span>
                      </td>

                      <td>
                        <div className="cell-actions">
                          <button
                            type="button"
                            className="btn btn--ghost btn--icon btn--sm"
                            onClick={() => openEditModal(course)}
                            aria-label={`Edit ${course.course_code}`}
                            title="Edit course"
                          >
                            <Pencil size={16} />
                          </button>

                          <button
                            type="button"
                            className="btn btn--danger-ghost btn--icon btn--sm"
                            onClick={() => setDeleteCourse(course)}
                            aria-label={`Delete ${course.course_code}`}
                            title="Delete course"
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
          )}
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
            className="modal modal--sm"
            role="dialog"
            aria-modal="true"
            aria-labelledby="course-modal-title"
          >
            <form onSubmit={handleSubmit}>
              <div className="modal__header">
                <div>
                  <h2 className="modal__title" id="course-modal-title">
                    {editingCourse ? "Edit Course" : "Add Course"}
                  </h2>

                  <p className="text-sm text-muted">
                    Enter the course information below.
                  </p>
                </div>

                <button
                  type="button"
                  className="btn btn--ghost btn--icon"
                  onClick={closeModal}
                  disabled={saving}
                  aria-label="Close dialog"
                >
                  <X size={19} />
                </button>
              </div>

              <div className="modal__body">
                {formError && (
                  <div className="alert alert--error">
                    <div className="alert__body">{formError}</div>
                  </div>
                )}

                <div className="stack">
                  <div className="form-group">
                    <label
                      className="label label--required"
                      htmlFor="course_code"
                    >
                      Course Code
                    </label>

                    <input
                      id="course_code"
                      name="course_code"
                      className="input"
                      placeholder="e.g. CS301…"
                      maxLength={20}
                      value={formData.course_code}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label
                      className="label label--required"
                      htmlFor="course_name"
                    >
                      Course Name
                    </label>

                    <input
                      id="course_name"
                      name="course_name"
                      className="input"
                      placeholder="Enter course name…"
                      maxLength={150}
                      value={formData.course_name}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label
                      className="label label--required"
                      htmlFor="credit_hours"
                    >
                      Credit Hours
                    </label>

                    <input
                      id="credit_hours"
                      name="credit_hours"
                      type="number"
                      className="input"
                      min="1"
                      max="255"
                      step="1"
                      value={formData.credit_hours}
                      onChange={handleInputChange}
                      required
                    />
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

                <button
                  type="submit"
                  className={`btn btn--primary ${saving ? "is-loading" : ""}`}
                  disabled={saving}
                >
                  {saving
                    ? "Saving..."
                    : editingCourse
                      ? "Save Changes"
                      : "Add Course"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {deleteCourse && (
        <div className="modal-backdrop">
          <div
            className="modal modal--sm"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-course-title"
          >
            <div className="modal__header">
              <div>
                <h2 className="modal__title" id="delete-course-title">
                  Delete Course
                </h2>

                <p className="text-sm text-muted">
                  This action cannot be undone.
                </p>
              </div>

              <button
                type="button"
                className="btn btn--ghost btn--icon"
                onClick={() => setDeleteCourse(null)}
                disabled={saving}
                aria-label="Close dialog"
              >
                <X size={19} />
              </button>
            </div>

            <div className="modal__body">
              <p>
                Are you sure you want to delete{" "}
                <strong>{deleteCourse.course_code}</strong>
                {" — "}
                {deleteCourse.course_name}?
              </p>
            </div>

            <div className="modal__footer">
              <button
                className="btn btn--secondary"
                onClick={() => setDeleteCourse(null)}
                disabled={saving}
              >
                Cancel
              </button>

              <button
                className="btn btn--danger"
                onClick={handleDelete}
                disabled={saving}
              >
                {saving ? "Deleting..." : "Delete Course"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
