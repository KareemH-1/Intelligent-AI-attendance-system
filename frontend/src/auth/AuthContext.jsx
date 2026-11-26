import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import { TOKEN_KEY } from "./authToken";
import { AuthContext } from "./AuthContext";

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(() => Boolean(sessionStorage.getItem(TOKEN_KEY)));

    const clearSession = useCallback(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        setUser(null);
        setLoading(false);
    }, []);

    useEffect(() => {
        let active = true;
        const token = sessionStorage.getItem(TOKEN_KEY);

        const handleUnauthorized = () => clearSession();
        window.addEventListener("auth:unauthorized", handleUnauthorized);

        if (token) {
            api.get("/auth/me")
                .then((response) => {
                    if (active) setUser(response.data);
                })
                .catch(() => {
                    if (active) clearSession();
                })
                .finally(() => {
                    if (active) setLoading(false);
                });
        }

        return () => {
            active = false;
            window.removeEventListener("auth:unauthorized", handleUnauthorized);
        };
    }, [clearSession]);

    const login = async (identifier, password) => {
        const response = await api.post("/auth/login", { identifier, password });
        sessionStorage.setItem(TOKEN_KEY, response.data.access_token);
        setUser(response.data.user);
        return response.data.user;
    };

    const logout = useCallback(() => clearSession(), [clearSession]);

    const completePasswordChange = () => {
        setUser((current) => current && {
            ...current,
            must_change_password: false,
        });
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                login,
                logout,
                completePasswordChange,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

