"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ClipboardList, ChevronDown, ChevronRight, Filter } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AuditEntry {
    id: string;
    user_id: string | null;
    action: string;
    resource_type: string | null;
    resource_id: string | null;
    details: Record<string, unknown>;
    ip_address: string | null;
    created_at: string | null;
}

export default function AuditLogPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [logs, setLogs] = useState<AuditEntry[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState<string | null>(null);
    const [actions, setActions] = useState<string[]>([]);
    const [filterAction, setFilterAction] = useState(searchParams.get("action") ?? "");
    const [filterUser, setFilterUser] = useState(searchParams.get("user_id") ?? "");
    const page = parseInt(searchParams.get("page") ?? "1", 10);
    const limit = 25;

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch(`${API}/audit/actions`, {
                    headers: { Authorization: `Bearer ${localStorage.getItem("sf_token")}` },
                });
                if (res.ok) {
                    const data = await res.json();
                    setActions(data.actions ?? []);
                }
            } catch { /* ignore */ }
        })();
    }, []);

    useEffect(() => {
        setLoading(true);
        const params = new URLSearchParams();
        params.set("limit", String(limit));
        params.set("offset", String((page - 1) * limit));
        if (filterAction) params.set("action", filterAction);
        if (filterUser) params.set("user_id", filterUser);

        fetch(`${API}/audit?${params}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem("sf_token")}` },
        })
            .then((r) => r.json())
            .then((data) => {
                setLogs(data.items ?? []);
                setTotal(data.total ?? 0);
            })
            .catch(() => setLogs([]))
            .finally(() => setLoading(false));
    }, [page, filterAction, filterUser]);

    const totalPages = Math.ceil(total / limit);

    const navigate = (p: number) => {
        const params = new URLSearchParams();
        params.set("page", String(p));
        if (filterAction) params.set("action", filterAction);
        if (filterUser) params.set("user_id", filterUser);
        router.push(`/audit?${params}`);
    };

    const actionColor = (action: string) => {
        if (action.startsWith("auth.login_failed")) return "text-red-400";
        if (action.startsWith("auth.")) return "text-blue-400";
        if (action.startsWith("attack.")) return "text-orange-400";
        if (action.startsWith("admin.")) return "text-purple-400";
        return "text-zinc-400";
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <ClipboardList className="h-6 w-6 text-primary" />
                <h2 className="text-2xl font-bold">Audit Log</h2>
                <span className="ml-auto text-sm text-zinc-500">{total} total entries</span>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
                <Filter className="h-4 w-4 text-zinc-500" />
                <select
                    className="rounded border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm"
                    value={filterAction}
                    onChange={(e) => setFilterAction(e.target.value)}
                >
                    <option value="">All actions</option>
                    {actions.map((a) => (
                        <option key={a} value={a}>{a}</option>
                    ))}
                </select>
                <input
                    type="text"
                    placeholder="Filter by user ID..."
                    className="rounded border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm w-56"
                    value={filterUser}
                    onChange={(e) => setFilterUser(e.target.value)}
                />
                {(filterAction || filterUser) && (
                    <button
                        className="text-xs text-zinc-500 hover:text-zinc-300"
                        onClick={() => { setFilterAction(""); setFilterUser(""); }}
                    >
                        Clear
                    </button>
                )}
            </div>

            {/* Table */}
            <div className="overflow-x-auto rounded-lg border border-zinc-800">
                <table className="w-full text-sm">
                    <thead className="border-b border-zinc-800 bg-zinc-900/70">
                        <tr>
                            <th className="px-4 py-3 text-left font-medium text-zinc-400 w-8"></th>
                            <th className="px-4 py-3 text-left font-medium text-zinc-400">Timestamp</th>
                            <th className="px-4 py-3 text-left font-medium text-zinc-400">Action</th>
                            <th className="px-4 py-3 text-left font-medium text-zinc-400">User</th>
                            <th className="px-4 py-3 text-left font-medium text-zinc-400">Resource</th>
                            <th className="px-4 py-3 text-left font-medium text-zinc-400">IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading && (
                            <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-500">Loading...</td></tr>
                        )}
                        {!loading && logs.length === 0 && (
                            <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-500">No audit entries found</td></tr>
                        )}
                        {!loading && logs.map((log) => (
                            <>
                                <tr
                                    key={log.id}
                                    className="border-b border-zinc-800/50 hover:bg-zinc-800/30 cursor-pointer transition-colors"
                                    onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                                >
                                    <td className="px-4 py-3">
                                        {expanded === log.id
                                            ? <ChevronDown className="h-4 w-4 text-zinc-500" />
                                            : <ChevronRight className="h-4 w-4 text-zinc-500" />
                                        }
                                    </td>
                                    <td className="px-4 py-3 text-zinc-300 whitespace-nowrap font-mono text-xs">
                                        {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                                    </td>
                                    <td className={`px-4 py-3 font-medium ${actionColor(log.action)}`}>
                                        {log.action}
                                    </td>
                                    <td className="px-4 py-3 text-zinc-300 font-mono text-xs">{log.user_id ?? "—"}</td>
                                    <td className="px-4 py-3 text-zinc-300">
                                        {log.resource_type ? `${log.resource_type}/${log.resource_id ?? ""}` : "—"}
                                    </td>
                                    <td className="px-4 py-3 text-zinc-500 font-mono text-xs">{log.ip_address ?? "—"}</td>
                                </tr>
                                {expanded === log.id && (
                                    <tr key={`${log.id}-details`} className="border-b border-zinc-800/50">
                                        <td colSpan={6} className="px-4 py-4 bg-zinc-900/50">
                                            <div className="text-xs font-medium text-zinc-500 mb-1">Details</div>
                                            <pre className="text-xs text-zinc-400 font-mono bg-zinc-950 rounded p-3 overflow-x-auto">
                                                {JSON.stringify(log.details, null, 2)}
                                            </pre>
                                        </td>
                                    </tr>
                                )}
                            </>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                    <button
                        className="rounded px-3 py-1 text-sm border border-zinc-700 disabled:opacity-40"
                        disabled={page <= 1}
                        onClick={() => navigate(page - 1)}
                    >
                        Previous
                    </button>
                    <span className="text-sm text-zinc-500">
                        Page {page} of {totalPages}
                    </span>
                    <button
                        className="rounded px-3 py-1 text-sm border border-zinc-700 disabled:opacity-40"
                        disabled={page >= totalPages}
                        onClick={() => navigate(page + 1)}
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}
