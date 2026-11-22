
import { useEffect, useState } from "react";
import {
    Plus,
    Pencil,
    Power,
    X,
    RefreshCw,
    CalendarDays,
    AlertCircle,
    Search,
    BookOpen,
    Trash2
} from "lucide-react";
import api from "../../services/api";

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(`${value.slice(0, 10)}T00:00:00`);

    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

function getErrorMessage(error) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail.map(item => item.msg).join(", ");
    }

    return error.message || "Something went wrong. Please try again.";
}

export default function SemestersPage() {
    const [semesters, setSemesters] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const [pageError, setPageError] = useState("");
    const [successMessage, setSuccessMessage] = useState("");

    const [modalOpen, setModalOpen] = useState(false);
    const [editingSemester, setEditingSemester] = useState(null);

    const [formData, setFormData] = useState({
        semester_name: "",
        start_date: "",
        end_date: "",
        copy_course_offerings: true
    });

    const [offeringSemester, setOfferingSemester] = useState(null);
    const [offeringSearch, setOfferingSearch] = useState("");
    const [courseSearch, setCourseSearch] = useState("");
    const [courseResults, setCourseResults] = useState([]);
    const [courseOffset, setCourseOffset] = useState(0);
    const [courseHasMore, setCourseHasMore] = useState(false);
    const [offerings, setOfferings] = useState([]);

    const [formError, setFormError] = useState("");

    const [pendingAction, setPendingAction] = useState(null);

    async function loadSemesters() {
        setLoading(true);
        setPageError("");

        try {
            const response = await api.get("/semesters");
            setSemesters(response.data);
        } catch (error) {
            setPageError(getErrorMessage(error));
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadSemesters();
    }, []);

    useEffect(() => {
        if (!offeringSemester) return;

        const timeoutId = setTimeout(() => {
            loadSemesterOfferings(offeringSemester, offeringSearch).catch((error) => {
                setFormError(getErrorMessage(error));
            });
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [offeringSearch, offeringSemester]);

    useEffect(() => {
        if (!offeringSemester) return;

        const timeoutId = setTimeout(() => {
            searchAvailableCourses();
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [courseSearch, offeringSemester]);

    function openCreateModal() {
        setEditingSemester(null);

        setFormData({
            semester_name: "",
            start_date: "",
            end_date: "",
            copy_course_offerings: true
        });

        setFormError("");
        setModalOpen(true);
    }

    function openEditModal(semester) {
        setEditingSemester(semester);

        setFormData({
            semester_name: semester.semester_name,
            start_date: semester.start_date.slice(0, 10),
            end_date: semester.end_date.slice(0, 10),
            copy_course_offerings: false
        });

        setFormError("");
        setModalOpen(true);
    }

    function closeModal() {
        if (saving) return;

        setModalOpen(false);
        setEditingSemester(null);
        setFormError("");
    }

    function handleInputChange(event) {
        const { name, value, type, checked } = event.target;

        setFormData(previous => ({
            ...previous,
            [name]: type === "checkbox" ? checked : value
        }));
    }

    async function handleSubmit(event) {
        event.preventDefault();
        setFormError("");
        setSuccessMessage("");

        const name = formData.semester_name.trim();

        if (!name) {
            setFormError("Semester name is required.");
            return;
        }

        if (name.length > 50) {
            setFormError("Semester name cannot exceed 50 characters.");
            return;
        }

        if (!formData.start_date || !formData.end_date) {
            setFormError("Both dates are required.");
            return;
        }

        if (formData.end_date < formData.start_date) {
            setFormError("End date cannot be before the start date.");
            return;
        }

        const payload = {
            semester_name: name,
            start_date: formData.start_date,
            end_date: formData.end_date,
            copy_course_offerings: editingSemester
                ? false
                : formData.copy_course_offerings
        };

        setSaving(true);

        try {
            if (editingSemester) {
                await api.put(
                    `/semesters/${editingSemester.semester_id}`,
                    payload
                );

                setSuccessMessage("Semester updated successfully.");
            } else {
                const response = await api.post("/semesters", payload);
                const copiedCount = response.data.copied_offerings_count;

                setSuccessMessage(
                    payload.copy_course_offerings &&
                    typeof copiedCount === "number" &&
                    copiedCount > 0
                        ? `Semester created successfully. ${copiedCount} course offering${copiedCount === 1 ? "" : "s"} copied from the previous semester.`
                        : "Semester created successfully."
                );
            }

            setModalOpen(false);
            setEditingSemester(null);

            await loadSemesters();
        } catch (error) {
            setFormError(getErrorMessage(error));
        } finally {
            setSaving(false);
        }
    }

    async function requestActivation(semester) {
    setSaving(true);
    setPageError("");
    setSuccessMessage("");

    try {
        const response = await api.patch(
            `/semesters/${semester.semester_id}/activate`,
            { confirm: false }
        );

        if (response.data.status === "confirmation_required") {
            setPendingAction({
                type: "confirm-activation",
                semester,
                message: response.data.message
            });

            return;
        }

        setSuccessMessage(response.data.message);
        await loadSemesters();

    } catch (error) {
        setPageError(getErrorMessage(error));
    } finally {
        setSaving(false);
    }
}

    function requestDeactivation(semester) {
        setPendingAction({
            type: "deactivate",
            semester
        });
    }

    async function executePendingAction() {
    if (!pendingAction) return;

    const { type, semester } = pendingAction;

    setSaving(true);
    setPageError("");
    setSuccessMessage("");

    try {
        if (type === "confirm-activation") {
            const response = await api.patch(
                `/semesters/${semester.semester_id}/activate`,
                { confirm: true }
            );

            setSuccessMessage(response.data.message);
        } else if (type === "deactivate") {
            const response = await api.patch(
                `/semesters/${semester.semester_id}/deactivate`
            );

            setSuccessMessage(response.data.message);
        }

        setPendingAction(null);
        await loadSemesters();

    } catch (error) {
        setPendingAction(null);
        setPageError(getErrorMessage(error));
    } finally {
        setSaving(false);
    }
}

    function closeConfirmation() {
        if (saving) return;
        setPendingAction(null);
    }

    async function loadSemesterOfferings(semester, searchValue = "") {
        const response = await api.get("/courses/offerings", {
            params: {
                semester_id: semester.semester_id,
                search: searchValue
            }
        });
        setOfferings(response.data);
    }

    async function openOfferingsModal(semester) {
        setOfferingSemester(semester);
        setOfferingSearch("");
        setCourseSearch("");
        setCourseOffset(0);
        setPageError("");
        setFormError("");

        try {
            await loadSemesterOfferings(semester);
            const coursesResponse = await api.get("/courses/search-options", {
                params: {
                    search: "",
                    limit: 20,
                    offset: 0,
                    semester_id: semester.semester_id
                }
            });
            setCourseResults(coursesResponse.data.items);
            setCourseHasMore(coursesResponse.data.has_more);
        } catch (error) {
            setFormError(getErrorMessage(error));
        }
    }

    async function searchAvailableCourses(reset = true) {
        try {
            const nextOffset = reset ? 0 : courseOffset + 20;
            const response = await api.get("/courses/search-options", {
                params: {
                    search: courseSearch,
                    limit: 20,
                    offset: nextOffset,
                    semester_id: offeringSemester?.semester_id
                }
            });
            setCourseResults(reset
                ? response.data.items
                : (previous) => [...previous, ...response.data.items]);
            setCourseOffset(nextOffset);
            setCourseHasMore(response.data.has_more);
        } catch (error) {
            setFormError(getErrorMessage(error));
        }
    }

    async function addCourseOffering(course) {
        setSaving(true);
        setFormError("");

        try {
            await api.post("/courses/offerings", {
                course_id: course.course_id,
                semester_id: offeringSemester.semester_id,
            });
            await loadSemesterOfferings(offeringSemester, offeringSearch);
            await searchAvailableCourses();
            setSuccessMessage("Course offering added successfully.");
        } catch (error) {
            setFormError(getErrorMessage(error));
        } finally {
            setSaving(false);
        }
    }

    async function removeCourseOffering(offering) {
        setSaving(true);
        setFormError("");

        try {
            await api.delete(`/courses/offerings/${offering.offering_id}`);
            await loadSemesterOfferings(offeringSemester, offeringSearch);
            await searchAvailableCourses();
            setSuccessMessage("Course offering removed successfully.");
        } catch (error) {
            setFormError(getErrorMessage(error));
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="page">

            <div className="page-header">
                <div className="page-header__text">
                    <h1 className="page-header__title">
                        Semester Management
                    </h1>

                    <p className="page-header__subtitle">
                        Create and manage academic semesters and
                        control the currently active semester.
                    </p>
                </div>

                <div className="page-header__actions">
                    <button
                        type="button"
                        className="btn btn--primary"
                        onClick={openCreateModal}
                    >
                        <Plus size={18} />
                        Add semester
                    </button>
                </div>
            </div>

            {/* Feedback */}
            {pageError && (
                <div className="alert alert--error">
                    <AlertCircle size={18} />

                    <div className="alert__body">
                        {pageError}
                    </div>

                    <button
                        type="button"
                        className="btn btn--ghost btn--icon"
                        onClick={() => setPageError("")}
                        aria-label="Dismiss error"
                    >
                        <X size={16} />
                    </button>
                </div>
            )}

            {successMessage && (
                <div className="alert alert--success">
                    <div className="alert__body">
                        {successMessage}
                    </div>

                    <button
                        type="button"
                        className="btn btn--ghost btn--icon"
                        onClick={() => setSuccessMessage("")}
                        aria-label="Dismiss message"
                    >
                        <X size={16} />
                    </button>
                </div>
            )}

            {/* Semester table */}
            <section className="card"
            style={{padding: "1rem", marginTop: "1rem", borderRadius: "0.5rem", boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)"}}>

                <div className="section__header">
                    <div>
                        <h2 className="section__title">
                            All semesters
                        </h2>

                        <p className="form-hint">
                            {semesters.length} semester
                            {semesters.length === 1 ? "" : "s"} registered
                        </p>
                    </div>

                    <button
                        type="button"
                        className="btn btn--secondary btn--sm"
                        onClick={loadSemesters}
                        disabled={loading}
                    >
                        <RefreshCw size={15} />
                        Refresh
                    </button>
                </div>

                {loading ? (
                    <div className="loading-state">
                        Loading semesters...
                    </div>
                ) : semesters.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state__icon">
                            <CalendarDays size={24} />
                        </div>

                        <h3 className="empty-state__title">
                            No semesters yet
                        </h3>

                        <p className="empty-state__text">
                            Create your first academic semester
                            to get started.
                        </p>

                        <button
                            type="button"
                            className="btn btn--primary"
                            onClick={openCreateModal}
                        >
                            <Plus size={17} />
                            Add semester
                        </button>
                    </div>
                ) : (
                    <div className="table-wrap">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Semester</th>
                                    <th>Start date</th>
                                    <th>End date</th>
                                    <th>Status</th>
                                    <th className="cell-actions">
                                        Actions
                                    </th>
                                </tr>
                            </thead>

                            <tbody>
                                {semesters.map(semester => (
                                    <tr key={semester.semester_id}>
                                        <td>
                                            <strong>
                                                {semester.semester_name}
                                            </strong>
                                        </td>

                                        <td>
                                            {formatDate(semester.start_date)}
                                        </td>

                                        <td>
                                            {formatDate(semester.end_date)}
                                        </td>

                                        <td>
                                            {semester.is_active ? (
                                                <span className="badge badge--success">
                                                    Active
                                                </span>
                                            ) : (
                                                <span className="badge">
                                                    Inactive
                                                </span>
                                            )}
                                        </td>

                                        <td className="cell-actions">
                                            <div className="cluster cluster--end"
                                            style={{display: "flex", flexDirection: "row", gap: "0.5rem"}}>
                                                <button
                                                    type="button"
                                                    className="btn btn--ghost btn--icon btn--sm"
                                                    onClick={() => openOfferingsModal(semester)}
                                                    title="Manage course offerings"
                                                    aria-label={`Manage course offerings for ${semester.semester_name}`}
                                                >
                                                    <BookOpen size={16} />
                                                </button>

                                                <button
                                                    type="button"
                                                    className="btn btn--ghost btn--icon btn--sm"
                                                    onClick={() => openEditModal(semester)}
                                                    title="Edit semester"
                                                    aria-label={`Edit ${semester.semester_name}`}
                                                >
                                                    <Pencil size={16} />
                                                </button>

                                                {semester.is_active ? (
                                                    <button
                                                        type="button"
                                                        className="btn btn--danger-ghost btn--icon btn--sm"
                                                        onClick={() => requestDeactivation(semester)}
                                                        title="Deactivate semester"
                                                        aria-label={`Deactivate ${semester.semester_name}`}
                                                    >
                                                        <Power size={16} />
                                                    </button>
                                                ) : (
                                                    <button
                                                        type="button"
                                                        className="btn btn--ghost btn--icon btn--sm"
                                                        onClick={() => requestActivation(semester)}
                                                        title="Activate semester"
                                                        aria-label={`Activate ${semester.semester_name}`}
                                                    >
                                                        <Power size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

            </section>

            {/* Create / Edit modal */}
            {modalOpen && (
                <div className="modal-backdrop">
                    <section
                        className="modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="semester-modal-title"
                    >
                        <div className="modal__header">
                            <div>
                                <h2
                                    id="semester-modal-title"
                                    className="modal__title"
                                >
                                    {editingSemester
                                        ? "Edit semester"
                                        : "Add semester"}
                                </h2>

                                <p className="form-hint">
                                    Enter the semester name and its dates.
                                </p>
                            </div>

                            <button
                                type="button"
                                className="btn btn--ghost btn--icon"
                                onClick={closeModal}
                                disabled={saving}
                                aria-label="Close dialog"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit}>
                            <div className="modal__body">

                                {formError && (
                                    <div className="alert alert--error">
                                        <AlertCircle size={17} />
                                        <div className="alert__body">
                                            {formError}
                                        </div>
                                    </div>
                                )}

                                <div className="form-group">
                                    <label
                                        className="label label--required"
                                        htmlFor="semester_name"
                                    >
                                        Semester name
                                    </label>

                                    <input
                                        id="semester_name"
                                        name="semester_name"
                                        type="text"
                                        className="input"
                                        placeholder="e.g. Fall 2026"
                                        maxLength={50}
                                        value={formData.semester_name}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>

                                <div className="form-group">
                                    <label
                                        className="label label--required"
                                        htmlFor="start_date"
                                    >
                                        Start date
                                    </label>

                                    <input
                                        id="start_date"
                                        name="start_date"
                                        type="date"
                                        className="input"
                                        value={formData.start_date}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>

                                <div className="form-group">
                                    <label
                                        className="label label--required"
                                        htmlFor="end_date"
                                    >
                                        End date
                                    </label>

                                    <input
                                        id="end_date"
                                        name="end_date"
                                        type="date"
                                        className="input"
                                        min={formData.start_date || undefined}
                                        value={formData.end_date}
                                        onChange={handleInputChange}
                                        required
                                    />
                                </div>

                                {!editingSemester && (
                                    <label className="check" htmlFor="copy_course_offerings">
                                        <input
                                            id="copy_course_offerings"
                                            name="copy_course_offerings"
                                            type="checkbox"
                                            checked={formData.copy_course_offerings}
                                            onChange={handleInputChange}
                                        />
                                        <span>
                                            Copy course offerings from the most recent semester
                                        </span>
                                    </label>
                                )}

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
                                    className="btn btn--primary"
                                    disabled={saving}
                                >
                                    {saving
                                        ? "Saving..."
                                        : editingSemester
                                            ? "Save changes"
                                            : "Create semester"}
                                </button>
                            </div>
                        </form>
                    </section>
                </div>
            )}

            {offeringSemester && (
                <div className="modal-backdrop">
                    <section
                        className="modal modal--lg"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="offerings-modal-title"
                    >
                        <div className="modal__header">
                            <div>
                                <h2 id="offerings-modal-title" className="modal__title">
                                    Course Offerings
                                </h2>
                                <p className="form-hint">
                                    {offeringSemester.semester_name}
                                </p>
                            </div>
                            <button
                                type="button"
                                className="btn btn--ghost btn--icon"
                                onClick={() => setOfferingSemester(null)}
                                disabled={saving}
                                aria-label="Close course offerings"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="modal__body">
                            {formError && (
                                <div className="alert alert--error">
                                    <div className="alert__body">{formError}</div>
                                </div>
                            )}

                            <div className="toolbar">
                                <div className="search">
                                    <Search size={18} className="search__icon" />
                                    <input
                                        className="input"
                                        type="text"
                                        role="searchbox"
                                        placeholder="Search course offerings..."
                                        value={offeringSearch}
                                        onChange={(event) => setOfferingSearch(event.target.value)}
                                    />
                                </div>
                            </div>

                            <div className="card card--flat" style={{ marginBottom: "1rem" }}>
                                <div className="card__body">
                                    <div className="toolbar">
                                        <div className="search">
                                            <Search size={18} className="search__icon" />
                                            <input
                                                className="input"
                                                type="text"
                                                role="searchbox"
                                                placeholder="Search courses to add..."
                                                value={courseSearch}
                                                onChange={(event) => setCourseSearch(event.target.value)}
                                            />
                                        </div>
                                    </div>

                                    {courseResults.map((course) => (
                                        <div
                                            key={course.course_id}
                                            className="cluster cluster--between"
                                            style={{
                                                padding: "0.75rem 0",
                                                borderTop: "1px solid var(--border-subtle)"
                                            }}
                                        >
                                            <span>
                                                <strong>{course.course_code}</strong>
                                                {" — "}
                                                {course.course_name}
                                            </span>
                                            <button
                                                type="button"
                                                className="btn btn--primary btn--sm"
                                                onClick={() => addCourseOffering(course)}
                                                disabled={saving}
                                            >
                                                <Plus size={15} />
                                                Add
                                            </button>
                                        </div>
                                    ))}
                                    {courseHasMore && (
                                        <button
                                            type="button"
                                            className="btn btn--secondary btn--block"
                                            onClick={() => searchAvailableCourses(false)}
                                            disabled={saving}
                                        >
                                            Load more courses
                                        </button>
                                    )}
                                </div>
                            </div>

                            <div className="table-wrap">
                                <table className="table">
                                    <thead>
                                        <tr>
                                            <th>Course</th>
                                            <th>Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {offerings.map((offering) => (
                                            <tr key={offering.offering_id}>
                                                <td>
                                                    <strong>{offering.course_code}</strong>
                                                    {" — "}
                                                    {offering.course_name}
                                                </td>
                                                <td>
                                                    <button
                                                        type="button"
                                                        className="btn btn--danger-ghost btn--icon btn--sm"
                                                        onClick={() => removeCourseOffering(offering)}
                                                        disabled={saving}
                                                        title="Remove offering"
                                                        aria-label={`Remove ${offering.course_code}`}
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                        {offerings.length === 0 && (
                                            <tr>
                                                <td colSpan="2">
                                                    <div className="empty-state">
                                                        No course offerings found for this semester.
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div className="modal__footer">
                            <button
                                type="button"
                                className="btn btn--secondary"
                                onClick={() => setOfferingSemester(null)}
                            >
                                Close
                            </button>
                        </div>
                    </section>
                </div>
            )}

            {/* Activation / Deactivation confirmation */}
            {pendingAction && (
                <div className="modal-backdrop">
                    <section
                        className="modal modal--sm"
                        role="alertdialog"
                        aria-modal="true"
                        aria-labelledby="confirmation-title"
                    >
                        <div className="modal__header">
                            <h2
                                id="confirmation-title"
                                className="modal__title"
                            >
                                {pendingAction.type === "activate"
                                    ? "Activate semester?"
                                    : pendingAction.type === "confirm-activation"
                                        ? "Switch active semester?"
                                        : "Deactivate semester?"}
                            </h2>

                            <button
                                type="button"
                                className="btn btn--ghost btn--icon"
                                onClick={closeConfirmation}
                                disabled={saving}
                                aria-label="Close dialog"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        <div className="modal__body">
                            <p>
                                {pendingAction.type === "activate" && (
                                    <>
                                        Do you want to activate{" "}
                                        <strong>
                                            {pendingAction.semester.semester_name}
                                        </strong>
                                        ?
                                    </>
                                )}

                                {pendingAction.type === "confirm-activation" && (
                                    pendingAction.message ||
                                    "The currently active semester has not ended. Are you sure you want to switch?"
                                )}

                                {pendingAction.type === "deactivate" && (
                                    <>
                                        Are you sure you want to deactivate{" "}
                                        <strong>
                                            {pendingAction.semester.semester_name}
                                        </strong>
                                        ?
                                        There will be no active semester afterward.
                                    </>
                                )}
                            </p>
                        </div>

                        <div className="modal__footer">
                            <button
                                type="button"
                                className="btn btn--secondary"
                                onClick={closeConfirmation}
                                disabled={saving}
                            >
                                Cancel
                            </button>

                            <button
                                type="button"
                                className={
                                    pendingAction.type === "deactivate"
                                        ? "btn btn--danger"
                                        : "btn btn--primary"
                                }
                                onClick={executePendingAction}
                                disabled={saving}
                            >
                                {saving
                                    ? "Please wait..."
                                    : pendingAction.type === "deactivate"
                                        ? "Deactivate"
                                        : pendingAction.type === "confirm-activation"
                                            ? "Confirm switch"
                                            : "Continue"}
                            </button>
                        </div>
                    </section>
                </div>
            )}

        </div>
    );
}
