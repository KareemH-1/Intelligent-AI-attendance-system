import { Navigate } from "react-router";
import useAuth from "../auth/useAuth";

export default function AccessDeniedPage() {
    const { user, loading, logout } = useAuth();

    if (loading) {
        return <main className="auth-page"><p>Checking your session...</p></main>;
    }
    if (!user) return <Navigate to="/login" replace />;

    return (
        <main className="auth-page">
            <section className="card auth-card">
                <header className="auth-card__header">
                    <h1 className="page-header__title">Access denied</h1>
                    <p className="page-header__subtitle">
                        Your account does not have access to the administration portal.
                    </p>
                </header>
                <button className="btn btn--secondary btn--block" type="button" onClick={logout}>
                    Sign out
                </button>
            </section>
        </main>
    );
}
