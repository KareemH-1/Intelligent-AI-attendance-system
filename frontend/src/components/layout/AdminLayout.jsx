
import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import {
    CalendarDays,
    Menu,
    BookOpen,
    Users,
    X,
    PanelLeftClose,
    PanelLeftOpen
} from "lucide-react";

export default function AdminLayout() {
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    function handleSidebarToggle() {
        if (window.matchMedia("(max-width: 1023px)").matches) {
            setSidebarOpen(previous => !previous);
        } else {
            setSidebarCollapsed(previous => !previous);
        }
    }

    function closeSidebar() {
        setSidebarOpen(false);
    }

    const isMobile = window.matchMedia("(max-width: 1023px)").matches;

    return (
        <div
            className={`app-shell ${
                sidebarCollapsed ? "app-shell--collapsed" : ""
            }`}
        >
            <aside className={`sidebar ${sidebarOpen ? "is-open" : ""}`}>

                <div className="sidebar__brand">
                    <span className="sidebar__brand-text">
                        Intelligent Attendance System
                    </span>
                </div>

                <nav className="sidebar__nav">

                    <div className="nav-group-label">
                        ACADEMIC MANAGEMENT
                    </div>

                    <NavLink
                        to="/admin/semesters"
                        className={({ isActive }) =>
                            isActive ? "nav-item is-active" : "nav-item"
                        }
                        onClick={closeSidebar}
                        title="Semesters"
                    >
                        <CalendarDays
                            className="nav-item__icon"
                            size={18}
                        />

                        <span className="nav-item__label">
                            Semesters
                        </span>
                    </NavLink>
                    <NavLink
                        to="/admin/courses"
                        className={({ isActive }) =>
                            isActive ? "nav-item is-active" : "nav-item"
                        }
                        onClick={closeSidebar}
                        title="Courses"
                    >
                        <BookOpen
                            className="nav-item__icon"
                            size={18}
                        />
                        <span className="nav-item__label">
                            Courses
                        </span>
                    </NavLink>
                    <NavLink
                        to="/admin/students"
                        className={({ isActive }) =>
                            isActive ? "nav-item is-active" : "nav-item"
                        }
                        onClick={closeSidebar}
                        title="Students"
                    >
                        <Users
                            className="nav-item__icon"
                            size={18}
                        />
                        <span className="nav-item__label">
                            Students
                        </span>
                    </NavLink>
                </nav>



            </aside>

            <button
                type="button"
                className={`sidebar-backdrop ${
                    sidebarOpen ? "is-open" : ""
                }`}
                onClick={closeSidebar}
                aria-label="Close navigation"
                tabIndex={sidebarOpen ? 0 : -1}
            />

            <div className="app-main">

                <header className="topbar">

                    <button
                        type="button"
                        className="btn btn--ghost btn--icon topbar__menu-btn"
                        onClick={handleSidebarToggle}
                        aria-label={
                            isMobile
                                ? sidebarOpen
                                    ? "Close navigation"
                                    : "Open navigation"
                                : sidebarCollapsed
                                    ? "Expand sidebar"
                                    : "Collapse sidebar"
                        }
                        aria-expanded={
                            isMobile ? sidebarOpen : !sidebarCollapsed
                        }
                    >
                        {isMobile ? (
                            sidebarOpen
                                ? <X size={20} />
                                : <Menu size={20} />
                        ) : (
                            sidebarCollapsed
                                ? <PanelLeftOpen size={20} />
                                : <PanelLeftClose size={20} />
                        )}
                    </button>

                    <span className="topbar__title">
                        Administration
                    </span>

                </header>

                <Outlet />

            </div>
        </div>
    );
}
