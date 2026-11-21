
import { useEffect, useState } from "react";
import {
    Plus,
    Pencil,
    Power,
    X,
    RefreshCw,
    CalendarDays,
    AlertCircle
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
        end_date: ""
    });

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

    function openCreateModal() {
        setEditingSemester(null);

        setFormData({
            semester_name: "",
            start_date: "",
            end_date: ""
        });

        setFormError("");
        setModalOpen(true);
    }

    function openEditModal(semester) {
        setEditingSemester(semester);

        setFormData({
            semester_name: semester.semester_name,
            start_date: semester.start_date.slice(0, 10),
            end_date: semester.end_date.slice(0, 10)
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
        const { name, value } = event.target;

        setFormData(previous => ({
            ...previous,
            [name]: value
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
            end_date: formData.end_date
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
                await api.post("/semesters", payload);

                setSuccessMessage("Semester created successfully.");
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
