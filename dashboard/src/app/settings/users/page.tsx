"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import { Users, Plus, Trash2, Shield, X, Loader2, UserCheck } from "lucide-react";
import { useRouter } from "next/navigation";

interface UserInfo {
    id: string;
    username: string;
    role: string;
    is_active: boolean;
}

export default function UsersPage() {
    const { user: currentUser } = useAuth();
    const router = useRouter();
    const [users, setUsers] = useState<UserInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);

    // Redirect non-admins
    useEffect(() => {
        if (currentUser && currentUser.role !== "admin") {
            router.push("/");
        }
    }, [currentUser, router]);

    async function fetchUsers() {
        try {
            const data = await api.get<UserInfo[]>("/auth/users");
            setUsers(data);
        } catch {
            // Not authorized or error
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchUsers();
    }, []);

    async function handleRoleChange(userId: string, newRole: string) {
        try {
            await api.patch(`/auth/users/${userId}/role`, { role: newRole });
            fetchUsers();
        } catch {
            alert("Failed to update role.");
        }
    }

    async function handleDelete(userId: string, username: string) {
        if (!confirm(`Delete user "${username}"? This cannot be undone.`)) return;
        try {
            await api.delete(`/auth/users/${userId}`);
            fetchUsers();
        } catch (e) {
            const msg = e instanceof Error ? e.message : "Failed to delete user.";
            alert(msg);
        }
    }

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-64 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">User Management</h2>
                    <p className="text-sm text-muted-foreground">
                        Manage users and assign roles. Admin-only.
                    </p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> Add User
                </button>
            </div>

            {/* Role legend */}
            <div className="flex gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5 text-amber-400" /> Admin — Full control
                </span>
                <span className="flex items-center gap-1.5">
                    <UserCheck className="h-3.5 w-3.5 text-blue-400" /> Analyst — Run tests, schedule, reports
                </span>
            </div>

            {/* Users table */}
            <div className="rounded-xl border border-border bg-card">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                <th className="px-4 py-2 font-medium">Username</th>
                                <th className="px-4 py-2 font-medium">Role</th>
                                <th className="px-4 py-2 font-medium">Status</th>
                                <th className="px-4 py-2 font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map((u) => {
                                const isSelf = u.username === currentUser?.username;
                                return (
                                    <tr
                                        key={u.id}
                                        className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors"
                                    >
                                        <td className="px-4 py-2.5">
                                            <div className="flex items-center gap-2">
                                                <Users className="h-4 w-4 text-muted-foreground" />
                                                <span className="font-medium text-foreground">
                                                    {u.username}
                                                </span>
                                                {isSelf && (
                                                    <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                                                        YOU
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-2.5">
                                            {isSelf ? (
                                                <RoleBadge role={u.role} />
                                            ) : (
                                                <select
                                                    value={u.role === "operator" ? "analyst" : u.role}
                                                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                                    className="rounded-md border border-input bg-secondary px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                                                >
                                                    <option value="admin">Admin</option>
                                                    <option value="analyst">Analyst</option>
                                                </select>
                                            )}
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <span
                                                className={cn(
                                                    "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                                                    u.is_active
                                                        ? "bg-emerald-500/20 text-emerald-400"
                                                        : "bg-zinc-700/50 text-zinc-400"
                                                )}
                                            >
                                                {u.is_active ? "ACTIVE" : "DISABLED"}
                                            </span>
                                        </td>
                                        <td className="px-4 py-2.5">
                                            {!isSelf && (
                                                <button
                                                    onClick={() => handleDelete(u.id, u.username)}
                                                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                                    title="Delete user"
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Create user modal */}
            {showCreate && (
                <CreateUserModal
                    onClose={() => setShowCreate(false)}
                    onCreated={() => { setShowCreate(false); fetchUsers(); }}
                />
            )}
        </div>
    );
}

function RoleBadge({ role }: { role: string }) {
    const displayRole = role === "operator" ? "analyst" : role;
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                displayRole === "admin"
                    ? "bg-amber-500/20 text-amber-400"
                    : "bg-blue-500/20 text-blue-400"
            )}
        >
            {displayRole === "admin" ? (
                <Shield className="h-3 w-3" />
            ) : (
                <UserCheck className="h-3 w-3" />
            )}
            {displayRole.toUpperCase()}
        </span>
    );
}

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState("analyst");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await api.post("/auth/register", { username, password, role });
            onCreated();
        } catch {
            setError("Failed to create user. Username may already exist.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-foreground">Add User</h3>
                    <button
                        onClick={onClose}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                            {error}
                        </div>
                    )}

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">Username</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            minLength={3}
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                            placeholder="e.g. jane.analyst"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={12}
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                            placeholder="Min 12 characters"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">Role</label>
                        <div className="flex gap-2">
                            {["analyst", "admin"].map((r) => (
                                <button
                                    type="button"
                                    key={r}
                                    onClick={() => setRole(r)}
                                    className={cn(
                                        "flex-1 rounded-md border px-3 py-2 text-sm font-medium transition-colors",
                                        role === r
                                            ? "border-primary bg-primary/10 text-primary"
                                            : "border-input bg-secondary text-muted-foreground hover:text-foreground"
                                    )}
                                >
                                    {r === "admin" ? (
                                        <span className="flex items-center justify-center gap-1.5">
                                            <Shield className="h-3.5 w-3.5" /> Admin
                                        </span>
                                    ) : (
                                        <span className="flex items-center justify-center gap-1.5">
                                            <UserCheck className="h-3.5 w-3.5" /> Analyst
                                        </span>
                                    )}
                                </button>
                            ))}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                            {role === "admin"
                                ? "Full control: manage users, delete scans, mark false positives"
                                : "Run tests, schedule scans, generate reports. Cannot delete or modify."}
                        </p>
                    </div>

                    <button
                        type="submit"
                        disabled={loading || !username || !password}
                        className="flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {loading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            "Create User"
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
