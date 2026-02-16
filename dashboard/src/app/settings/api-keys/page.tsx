"use client";

import { useState } from "react";
import { useApiKeys } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { timeAgo, cn } from "@/lib/utils";
import { Key, Plus, Trash2, X, Copy, Check } from "lucide-react";
import { mutate } from "swr";

const AVAILABLE_SCOPES = ["read", "write", "admin"];

export default function ApiKeysPage() {
    const { data: keys, isLoading } = useApiKeys();
    const [showCreate, setShowCreate] = useState(false);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    const allKeys = keys ?? [];

    async function handleRevoke(id: string) {
        if (!confirm("Revoke this API key? This action cannot be undone.")) return;
        await api.delete(`/api-keys/${id}`);
        mutate("/api-keys");
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">API Keys</h2>
                    <p className="text-sm text-muted-foreground">
                        Manage API keys for CI/CD pipelines and external integrations
                    </p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> Create Key
                </button>
            </div>

            {/* Keys table */}
            <div className="rounded-xl border border-border bg-card">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                <th className="px-4 py-2 font-medium">Name</th>
                                <th className="px-4 py-2 font-medium">Prefix</th>
                                <th className="px-4 py-2 font-medium">Scopes</th>
                                <th className="px-4 py-2 font-medium">Created</th>
                                <th className="px-4 py-2 font-medium">Last Used</th>
                                <th className="px-4 py-2 font-medium">Expires</th>
                                <th className="px-4 py-2 font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {allKeys.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={7}
                                        className="px-4 py-12 text-center text-muted-foreground"
                                    >
                                        <Key className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
                                        No API keys created yet.
                                    </td>
                                </tr>
                            ) : (
                                allKeys.map((k) => (
                                    <tr
                                        key={k.id}
                                        className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors"
                                    >
                                        <td className="px-4 py-2.5 font-medium text-foreground">
                                            {k.name}
                                        </td>
                                        <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">
                                            {k.prefix}...
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <div className="flex gap-1">
                                                {k.scopes.map((s) => (
                                                    <span
                                                        key={s}
                                                        className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
                                                    >
                                                        {s}
                                                    </span>
                                                ))}
                                            </div>
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                            {timeAgo(k.created_at)}
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                            {k.last_used_at ? timeAgo(k.last_used_at) : "Never"}
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                            {k.expires_at
                                                ? new Date(k.expires_at).toLocaleDateString()
                                                : "Never"}
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <button
                                                onClick={() => handleRevoke(k.id)}
                                                className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                                title="Revoke"
                                            >
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Create modal */}
            {showCreate && (
                <CreateKeyModal onClose={() => setShowCreate(false)} />
            )}
        </div>
    );
}

function CreateKeyModal({ onClose }: { onClose: () => void }) {
    const [name, setName] = useState("");
    const [scopes, setScopes] = useState<string[]>(["read"]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [createdKey, setCreatedKey] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    function toggleScope(scope: string) {
        setScopes((prev) =>
            prev.includes(scope)
                ? prev.filter((s) => s !== scope)
                : [...prev, scope]
        );
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const resp = await api.post<{ key: string }>("/api-keys", {
                name,
                scopes,
            });
            setCreatedKey(resp.key);
            mutate("/api-keys");
        } catch {
            setError("Failed to create API key");
        } finally {
            setLoading(false);
        }
    }

    async function handleCopy() {
        if (createdKey) {
            await navigator.clipboard.writeText(createdKey);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-foreground">
                        {createdKey ? "API Key Created" : "Create API Key"}
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {createdKey ? (
                    <div className="space-y-4">
                        <div className="rounded-md bg-warning/10 px-3 py-2 text-sm text-warning">
                            ⚠️ Copy this key now — it will not be shown again.
                        </div>
                        <div className="flex items-center gap-2">
                            <code className="flex-1 overflow-x-auto rounded-md bg-secondary p-3 text-xs text-foreground font-mono">
                                {createdKey}
                            </code>
                            <button
                                onClick={handleCopy}
                                className="rounded-md p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                            >
                                {copied ? (
                                    <Check className="h-4 w-4 text-low" />
                                ) : (
                                    <Copy className="h-4 w-4" />
                                )}
                            </button>
                        </div>
                        <button
                            onClick={onClose}
                            className="flex h-10 w-full items-center justify-center rounded-md bg-secondary px-4 text-sm font-medium text-foreground hover:bg-secondary/80 transition-colors"
                        >
                            Done
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                                {error}
                            </div>
                        )}

                        <div className="space-y-1">
                            <label className="text-sm font-medium text-foreground">
                                Name
                            </label>
                            <input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                                placeholder="ci-pipeline"
                                className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium text-foreground">
                                Scopes
                            </label>
                            <div className="flex gap-2">
                                {AVAILABLE_SCOPES.map((s) => (
                                    <button
                                        type="button"
                                        key={s}
                                        onClick={() => toggleScope(s)}
                                        className={cn(
                                            "rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                                            scopes.includes(s)
                                                ? "border-primary bg-primary/10 text-primary"
                                                : "border-input bg-secondary text-muted-foreground hover:text-foreground"
                                        )}
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading || scopes.length === 0}
                            className="flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                        >
                            {loading ? "Creating..." : "Create Key"}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}
