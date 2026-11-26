import { useState } from "react";
import { Navigate, useNavigate } from "react-router";
import useAuth from "../auth/useAuth";
import api from "../services/api";

function getErrorMessage(error) {
    const detail = error?.response?.data?.detail;
    return typeof detail === "string" ? detail : "Unable to change your password. Please try again.";
}

export default function ChangePasswordPage() {
    const { user, loading, completePasswordChange } = useAuth();
    const navigate = useNavigate();
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [submitting, setSubmitting] = useState(false);

    if (loading) {
        return <main className="auth-page"><p>Checking your session...</p></main>;
    }
    if (!user) return <Navigate to="/login" replace />;
    if (!user.must_change_password) {
        return <Navigate to={user.role === "Admin" ? "/admin" : "/access-denied"} replace />;
    }

    const handleSubmit = async (event) => {
        event.preventDefault();
        setErrorMessage("");
        if (newPassword !== confirmPassword) {
            setErrorMessage("The new passwords do not match.");
            return;
        }

        setSubmitting(true);
        try {
            await api.post("/auth/change-password", {
                current_password: currentPassword,
                new_password: newPassword,
            });
            completePasswordChange();
            navigate(user.role === "Admin" ? "/admin" : "/access-denied", { replace: true });
        } catch (error) {
            setErrorMessage(getErrorMessage(error));
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <main className="auth-page">
            <section className="card auth-card">
                <header className="auth-card__header">
                    <h1 className="page-header__title">Change your password</h1>
                    <p className="page-header__subtitle">
                        Set a new password before continuing. Use at least 8 characters.
                    </p>
                </header>
                <form className="auth-form" onSubmit={handleSubmit}>
                    {errorMessage && <div className="alert alert--error" role="alert">{errorMessage}</div>}
                    <label className="form-field">
                        <span>Current password</span>
                        <input
                            className="input"
                            type="password"
                            autoComplete="current-password"
                            value={currentPassword}
                            onChange={(event) => setCurrentPassword(event.target.value)}
                            required
                        />
                    </label>
                    <label className="form-field">
                        <span>New password</span>
                        <input
                            className="input"
                            type="password"
                            autoComplete="new-password"
                            minLength={8}
                            value={newPassword}
                            onChange={(event) => setNewPassword(event.target.value)}
                            required
                        />
                    </label>
                    <label className="form-field">
                        <span>Confirm new password</span>
                        <input
                            className="input"
                            type="password"
                            autoComplete="new-password"
                            minLength={8}
                            value={confirmPassword}
                            onChange={(event) => setConfirmPassword(event.target.value)}
                            required
                        />
                    </label>
                    <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
                        {submitting ? "Updating..." : "Update password"}
                    </button>
                </form>
            </section>
        </main>
    );
}
