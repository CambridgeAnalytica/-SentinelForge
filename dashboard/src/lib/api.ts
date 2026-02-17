/**
 * SentinelForge API client.
 * Wraps fetch with JWT / API-key auth, JSON parsing, and error handling.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ── Token helpers ── */

export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("sf_token");
}

export function setToken(token: string) {
    localStorage.setItem("sf_token", token);
}

export function clearToken() {
    localStorage.removeItem("sf_token");
}

/* ── Core fetcher ── */

export class ApiError extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown) {
        super(`API ${status}`);
        this.status = status;
        this.body = body;
    }
}

export async function apiFetch<T = unknown>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(options.headers as Record<string, string>),
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (res.status === 401) {
        clearToken();
        if (typeof window !== "undefined") {
            window.location.href = "/login";
        }
        throw new ApiError(401, "Unauthorized");
    }

    if (!res.ok) {
        const body = await res.json().catch(() => res.statusText);
        throw new ApiError(res.status, body);
    }

    // Handle no-content responses
    if (res.status === 204) return undefined as T;

    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
        return res.json() as Promise<T>;
    }

    return res.blob() as unknown as T;
}

/* ── Convenience methods ── */

export const api = {
    get: <T = unknown>(path: string) => apiFetch<T>(path),
    post: <T = unknown>(path: string, body?: unknown) =>
        apiFetch<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
    put: <T = unknown>(path: string, body?: unknown) =>
        apiFetch<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
    delete: <T = unknown>(path: string) =>
        apiFetch<T>(path, { method: "DELETE" }),
};

/* ── Auth ── */

export async function login(username: string, password: string) {
    const data = await api.post<{ access_token: string; expires_in: number }>(
        "/auth/login",
        { username, password }
    );
    setToken(data.access_token);
    return data;
}

export async function logout() {
    try {
        await api.post("/auth/logout");
    } finally {
        clearToken();
    }
}
