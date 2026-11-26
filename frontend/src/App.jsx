
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthContext.jsx";
import useAuth from "./auth/useAuth";
import RequireAdmin from "./auth/RequireAdmin";
import AdminLayout from "./components/layout/AdminLayout";
import SemestersPage from "./pages/admin/SemestersPage";
import CoursesPage from "./pages/admin/CoursesPage";
import StudentsPage from "./pages/admin/StudentsPage";
import InstructorsPage from "./pages/admin/InstructorsPage";
import HallsPage from "./pages/admin/HallsPage";
import TimetablePage from "./pages/admin/TimetablePage";
import SessionHistoryPage from "./pages/admin/SessionHistoryPage";
import AccessDeniedPage from "./pages/AccessDeniedPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import LoginPage from "./pages/LoginPage";

function HomeRedirect() {
    const { user, loading } = useAuth();
    if (loading) return <main className="auth-page"><p>Checking your session...</p></main>;
    if (!user) return <Navigate to="/login" replace />;
    if (user.must_change_password) return <Navigate to="/change-password" replace />;
    return <Navigate to={user.role === "Admin" ? "/admin" : "/access-denied"} replace />;
}

export default function App() {
    return (
        <AuthProvider>
          <BrowserRouter>
            <Routes>
                <Route path="/" element={<HomeRedirect />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/change-password" element={<ChangePasswordPage />} />
                <Route path="/access-denied" element={<AccessDeniedPage />} />
                <Route element={<RequireAdmin />}>
                  <Route path="/admin" element={<AdminLayout />}>
                    <Route
                        index
                        element={<Navigate to="semesters" replace />}
                    />

                    <Route
                        path="semesters"
                        element={<SemestersPage />}
                    />
                    <Route
                        path="courses"
                        element={<CoursesPage />}
                    />
                    <Route
                        path="students"
                        element={<StudentsPage />}
                    />
                    <Route
                        path="instructors"
                        element={<InstructorsPage />}
                    />
                    <Route
                        path="halls"
                        element={<HallsPage />}
                    />
                    <Route
                        path="timetable"
                        element={<TimetablePage />}
                    />
                    <Route
                        path="sessions"
                        element={<SessionHistoryPage />}
                    />
                    </Route>
                </Route>

                <Route
                    path="*"
                      element={<Navigate to="/" replace />}
                />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
    );
}
