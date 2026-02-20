"use client";

import React, {
    createContext,
    useContext,
    useState,
    useCallback,
    useEffect,
} from "react";
import { getToken, login as apiLogin, logout as apiLogout, clearToken } from "./api";

interface User {
    username: string;
    role: string;
}

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    login: async () => { },
    logout: async () => { },
});

function getInitialUser(): User | null {
    if (typeof window === "undefined") return null;
    const token = getToken();
    if (!token) return null;
    try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        return { username: payload.sub ?? "admin", role: payload.role ?? "admin" };
    } catch {
        clearToken();
        return null;
    }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Resolve auth state client-side only to avoid SSR/client mismatch
    useEffect(() => {
        setUser(getInitialUser());
        setIsLoading(false);
    }, []);

    const login = useCallback(async (username: string, password: string) => {
        await apiLogin(username, password);
        // Parse role from JWT token
        const token = getToken();
        let role = "analyst";
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split(".")[1]));
                role = payload.role ?? "analyst";
            } catch { /* fallback to analyst */ }
        }
        setUser({ username, role });
    }, []);

    const logout = useCallback(async () => {
        await apiLogout();
        setUser(null);
    }, []);

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                isLoading,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
