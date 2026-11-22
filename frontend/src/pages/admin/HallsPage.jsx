import { useCallback, useEffect, useState } from "react";
import { Building2, Plus, Search, Pencil, Eye, Trash2, X, Power } from "lucide-react";

import api from "../../services/api";

const emptyForm = {
  hall_name: "",
  building: "",
  capacity: "",
  terminal_password: "",
};

function getErrorDetail(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(" ");
  }
  return fallback;
}

export default function HallsPage() {
  const [halls, setHalls] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingHall, setEditingHall] = useState(null);
  const [viewHall, setViewHall] = useState(null);
  const [deleteHall, setDeleteHall] = useState(null);
  const [formData, setFormData] = useState(emptyForm);
  const [formError, setFormError] = useState("");
  const [terminalPassword, setTerminalPassword] = useState("");

  const loadHalls = useCallback(async (searchValue = "", signal) => {
    try {
      setLoading(true);
      setPageError("");
      const response = await api.get("/halls", {
        params: { search: searchValue },
        signal,
      });
      setHalls(response.data);
    } catch (error) {
      if (!signal?.aborted) {
        setPageError(getErrorDetail(error, "Failed to load lecture halls."));
      }
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      loadHalls(search, controller.signal);
    }, 300);
    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [search, loadHalls]);

  const openCreateModal = () => {
    setEditingHall(null);
    setFormData(emptyForm);
    setFormError("");
    setModalOpen(true);
  };

  const openEditModal = (hall) => {
    setEditingHall(hall);
    setFormData({
      hall_name: hall.hall_name,
      building: hall.building,
      capacity: String(hall.capacity),
      terminal_password: "",
    });
    setFormError("");
    setModalOpen(true);
  };

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setEditingHall(null);
    setFormData(emptyForm);
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");

    const payload = {
      hall_name: formData.hall_name.trim(),
      building: formData.building.trim(),
      capacity: Number(formData.capacity),
    };

    if (!editingHall) {
      payload.terminal_password = formData.terminal_password;
    }

    if (!payload.hall_name || !payload.building) {
      setFormError("Hall name and building are required.");
      setSaving(false);
      return;
    }
    if (!Number.isInteger(payload.capacity) || payload.capacity <= 0) {
      setFormError("Capacity must be a positive whole number.");
      setSaving(false);
      return;
    }
    if (!editingHall && formData.terminal_password.length < 6) {
      setFormError("Terminal password must contain at least 6 characters.");
      setSaving(false);
      return;
    }
    if (editingHall && formData.terminal_password && formData.terminal_password.length < 6) {
      setFormError("New terminal password must contain at least 6 characters.");
      setSaving(false);
      return;
    }

    try {
      if (editingHall) {
        await api.put(`/halls/${editingHall.hall_id}`, payload);
        if (formData.terminal_password) {
          await api.patch(
            `/halls/${editingHall.hall_id}/terminal/password`,
            { terminal_password: formData.terminal_password },
          );
        }
        setSuccessMessage("Lecture hall updated successfully.");
      } else {
        await api.post("/halls", payload);
        setSuccessMessage("Lecture hall created successfully.");
      }
      closeModal();
      await loadHalls(search);
    } catch (error) {
      setFormError(getErrorDetail(error, "Unable to save lecture hall."));
    } finally {
      setSaving(false);
    }
  };

  const resetTerminalPassword = async () => {
    if (!viewHall || terminalPassword.length < 6) {
      setFormError("Terminal password must contain at least 6 characters.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      await api.patch(
        `/halls/${viewHall.hall_id}/terminal/password`,
        { terminal_password: terminalPassword },
      );
      setTerminalPassword("");
      setSuccessMessage("Hall terminal password updated successfully.");
      const hallResponse = await api.get(`/halls/${viewHall.hall_id}`);
      setViewHall(hallResponse.data);
    } catch (error) {
      setFormError(getErrorDetail(error, "Unable to update terminal password."));
    } finally {
      setSaving(false);
    }
  };

  const toggleTerminal = async () => {
    if (!viewHall) return;
    setSaving(true);
    setFormError("");
    try {
      const response = await api.patch(
        `/halls/${viewHall.hall_id}/terminal/status`,
        { is_active: !viewHall.terminal_active },
      );
      setViewHall({
        ...viewHall,
        terminal_active: response.data.is_active,
      });
      setSuccessMessage(response.data.message);
      await loadHalls(search);
    } catch (error) {
      setFormError(getErrorDetail(error, "Unable to change terminal status."));
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteHall) return;
    setSaving(true);
    setPageError("");
    try {
      const response = await api.delete(`/halls/${deleteHall.hall_id}`);
      setSuccessMessage(response.data.message);
      setDeleteHall(null);
      await loadHalls(search);
    } catch (error) {
      setPageError(getErrorDetail(error, "Unable to delete lecture hall."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <div>
            <h1>Lecture Halls</h1>
            <p className="text-muted">Create and manage campus lecture halls.</p>
          </div>
          <button type="button" className="btn btn--primary" onClick={openCreateModal}>
            <Plus size={18} /> Add Lecture Hall
          </button>
        </div>

        {successMessage && <div className="alert alert--success"><div className="alert__body">{successMessage}</div></div>}
        {pageError && <div className="alert alert--error"><div className="alert__body">{pageError}</div></div>}

        <section className="section">
          <div className="toolbar">
            <div className="search">
              <Search className="search__icon" size={18} />
              <input
                className="input"
                type="text"
                role="searchbox"
                placeholder="Search halls or buildings..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>

          <div className="card">
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Hall Name</th>
                    <th>Building</th>
                    <th>Capacity</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && (
                    <tr><td colSpan="4"><div className="loading-state"><div className="spinner" /><p>Loading halls...</p></div></td></tr>
                  )}
                  {!loading && halls.length === 0 && (
                    <tr><td colSpan="4"><div className="empty-state"><Building2 size={28} /><h3>No lecture halls found</h3></div></td></tr>
                  )}
                  {!loading && halls.map((hall) => (
                    <tr key={hall.hall_id}>
                      <td><span className="font-medium">{hall.hall_name}</span></td>
                      <td>{hall.building}</td>
                      <td>{hall.capacity}</td>
                      <td>
                        <div className="cell-actions">
                          <button type="button" className="btn btn--ghost btn--icon" title="View" onClick={() => setViewHall(hall)}><Eye size={16} /></button>
                          <button type="button" className="btn btn--ghost btn--icon" title="Edit" onClick={() => openEditModal(hall)}><Pencil size={16} /></button>
                          <button type="button" className="btn btn--danger-ghost btn--icon" title="Delete" onClick={() => setDeleteHall(hall)}><Trash2 size={16} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>

      {modalOpen && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closeModal();
        }}>
          <div className="modal modal--sm" role="dialog" aria-modal="true">
            <form onSubmit={handleSubmit}>
              <div className="modal__header">
                <h2 className="modal__title">{editingHall ? "Edit Lecture Hall" : "Add Lecture Hall"}</h2>
                <button type="button" className="btn btn--ghost btn--icon" onClick={closeModal}><X size={18} /></button>
              </div>
              <div className="modal__body">
                {formError && <div className="alert alert--error"><div className="alert__body">{formError}</div></div>}
                <div className="stack">
                  <div className="form-group">
                    <label className="label label--required" htmlFor="hall_name">Hall Name</label>
                    <input id="hall_name" className="input" maxLength={50} value={formData.hall_name} onChange={(event) => setFormData({ ...formData, hall_name: event.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label className="label label--required" htmlFor="building">Building</label>
                    <input id="building" className="input" maxLength={100} value={formData.building} onChange={(event) => setFormData({ ...formData, building: event.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label className="label label--required" htmlFor="capacity">Capacity</label>
                    <input id="capacity" type="number" className="input" min="1" step="1" value={formData.capacity} onChange={(event) => setFormData({ ...formData, capacity: event.target.value })} required />
                  </div>
                  <div className="form-group">
                    <label
                      className={editingHall ? "label" : "label label--required"}
                      htmlFor="terminal_password"
                    >
                      Hall Terminal Password
                    </label>
                    <input
                      id="terminal_password"
                      type="password"
                      className="input"
                      minLength={6}
                      maxLength={255}
                      value={formData.terminal_password}
                      onChange={(event) => setFormData({
                        ...formData,
                        terminal_password: event.target.value,
                      })}
                      placeholder={editingHall ? "Leave blank to keep the current password" : ""}
                      required={!editingHall}
                    />
                  </div>
                </div>
              </div>
              <div className="modal__footer">
                <button type="button" className="btn btn--secondary" onClick={closeModal}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={saving}>{saving ? "Saving..." : editingHall ? "Save Changes" : "Add Hall"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {viewHall && (
        <div className="modal-backdrop"><div className="modal modal--sm" role="dialog" aria-modal="true">
          <div className="modal__header"><h2 className="modal__title">Lecture Hall Details</h2><button type="button" className="btn btn--ghost btn--icon" onClick={() => setViewHall(null)}><X size={18} /></button></div>
          <div className="modal__body">
            <p><strong>{viewHall.hall_name}</strong></p>
            <p>Building: {viewHall.building}</p>
            <p>Capacity: {viewHall.capacity}</p>
            <p>Terminal: {viewHall.terminal_code || "Not configured"}</p>
            <p>Status: {viewHall.terminal_active ? "Active" : "Inactive"}</p>
            {formError && <div className="alert alert--error"><div className="alert__body">{formError}</div></div>}
            <div className="form-group" style={{ marginTop: "1rem" }}>
              <label className="label" htmlFor="reset_terminal_password">New Terminal Password</label>
              <input
                id="reset_terminal_password"
                type="password"
                className="input"
                minLength={6}
                maxLength={255}
                value={terminalPassword}
                onChange={(event) => setTerminalPassword(event.target.value)}
              />
            </div>
          </div>
          <div className="modal__footer">
            <button type="button" className="btn btn--secondary" onClick={toggleTerminal} disabled={saving}>
              <Power size={16} /> {viewHall.terminal_active ? "Deactivate Terminal" : "Activate Terminal"}
            </button>
            <button type="button" className="btn btn--secondary" onClick={resetTerminalPassword} disabled={saving || terminalPassword.length < 6}>
              Reset Password
            </button>
            <button type="button" className="btn btn--secondary" onClick={() => setViewHall(null)}>Close</button>
          </div>
        </div></div>
      )}

      {deleteHall && (
        <div className="modal-backdrop"><div className="modal modal--sm" role="alertdialog" aria-modal="true">
          <div className="modal__header"><h2 className="modal__title">Delete Lecture Hall</h2><button type="button" className="btn btn--ghost btn--icon" onClick={() => setDeleteHall(null)}><X size={18} /></button></div>
          <div className="modal__body"><p>Delete <strong>{deleteHall.hall_name}</strong> in {deleteHall.building}? This is blocked if the hall is used in schedules or terminals.</p></div>
          <div className="modal__footer"><button type="button" className="btn btn--secondary" onClick={() => setDeleteHall(null)}>Cancel</button><button type="button" className="btn btn--danger" onClick={confirmDelete} disabled={saving}>{saving ? "Deleting..." : "Delete Hall"}</button></div>
        </div></div>
      )}
    </div>
  );
}
