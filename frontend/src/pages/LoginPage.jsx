import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import useAuth from "../auth/useAuth";

function getErrorMessage(error) {
    const detail = error?.response?.data?.detail;
    return typeof detail === "string" ? detail : "Unable to sign in. Please try again.";
}

export default function LoginPage() {
    const { user, loading, login } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!user) return;
        if (user.must_change_password) {
            navigate("/change-password", { replace: true });
        } else if (user.role === "Admin") {
            navigate("/admin", { replace: true });
        } else {
            navigate("/access-denied", { replace: true });
        }
    }, [user, navigate]);

    if (loading) {
        return <main className="auth-page"><p>Checking your session...</p></main>;
    }
    if (user) return <Navigate to="/" replace />;

    const handleSubmit = async (event) => {
        event.preventDefault();
        setErrorMessage("");
        setSubmitting(true);
        try {
            const authenticatedUser = await login(identifier.trim(), password);
            if (authenticatedUser.must_change_password) {
                navigate("/change-password", { replace: true });
            } else if (authenticatedUser.role === "Admin") {
                navigate(location.state?.from?.pathname || "/admin", { replace: true });
            } else {
                navigate("/access-denied", { replace: true });
            }
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
                    <h1 className="page-header__title">Sign in</h1>
                    <p className="page-header__subtitle">Intelligent Attendance System</p>
                </header>
                <form className="auth-form" onSubmit={handleSubmit}>
                    {errorMessage && <div className="alert alert--error" role="alert">{errorMessage}</div>}
                    <label className="form-field">
                        <span>University ID or email</span>
                        <input
                            className="input"
                            autoComplete="username"
                            maxLength={150}
                            placeholder="Enter your university ID or email"
                            value={identifier}
                            onChange={(event) => setIdentifier(event.target.value)}
                            required
                        />
                    </label>
                    <label className="form-field">
                        <span>Password</span>
                        <input
                            className="input"
                            type="password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                            required
                        />
                    </label>
                    <button className="btn btn--primary btn--block" type="submit" disabled={submitting}>
                        {submitting ? "Signing in..." : "Sign in"}
                    </button>
                </form>
            </section>
        </main>
    );
}
