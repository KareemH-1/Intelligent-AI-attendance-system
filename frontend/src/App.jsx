
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import AdminLayout from "./components/layout/AdminLayout";
import SemestersPage from "./pages/admin/SemestersPage";

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/admin" element={<AdminLayout />}>
                    <Route
                        index
                        element={<Navigate to="semesters" replace />}
                    />

                    <Route
                        path="semesters"
                        element={<SemestersPage />}
                    />
                </Route>

                <Route
                    path="*"
                    element={<Navigate to="/admin/semesters" replace />}
                />
            </Routes>
        </BrowserRouter>
    );
}
