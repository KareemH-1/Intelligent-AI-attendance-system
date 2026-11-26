import { Navigate, Outlet, useLocation } from "react-router";
import useAuth from "./useAuth";

export default function RequireAdmin() {
    const { user, loading } = useAuth();
    const location = useLocation();

    if (loading) {
        return <main className="auth-page"><p>Checking your session...</p></main>;
    }
    if (!user) {
        return <Navigate to="/login" replace state={{ from: location }} />;
    }
    if (user.must_change_password) {
        return <Navigate to="/change-password" replace />;
    }
    if (user.role !== "Admin") {
        return <Navigate to="/access-denied" replace />;
    }

    return <Outlet />;
}
