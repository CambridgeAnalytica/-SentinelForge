"use client";

import { useState } from "react";
import { useWebhooks, type Webhook } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";
import {
    Globe,
    Plus,
    Trash2,
    TestTube,
    X,
    Copy,
    Check,
} from "lucide-react";
import { mutate } from "swr";

const AVAILABLE_EVENTS = [
    "attack.completed",
    "attack.failed",
    "scan.completed",
    "report.generated",
    "agent.test.completed",
];

export default function WebhooksPage() {
    const { data: webhooks, isLoading } = useWebhooks();
    const [showCreate, setShowCreate] = useState(false);
    const [copiedId, setCopiedId] = useState<string | null>(null);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    const allWebhooks = webhooks ?? [];

    async function handleDelete(id: string) {
        if (!confirm("Delete this webhook endpoint?")) return;
        await api.delete(`/webhooks/${id}`);
        mutate("/webhooks");
    }

    async function handleTest(id: string) {
        try {
            await api.post(`/webhooks/${id}/test`);
        } catch {
            // silent
        }
    }

    async function copyUrl(wh: Webhook) {
        await navigator.clipboard.writeText(wh.url);
        setCopiedId(wh.id);
        setTimeout(() => setCopiedId(null), 2000);
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">
                        Webhook Endpoints
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Receive real-time HTTP callbacks when events occur in SentinelForge
                    </p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> Add Webhook
                </button>
            </div>

            {/* Webhook List */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">
                        Registered Endpoints ({allWebhooks.length})
                    </h3>
                </div>
                <div className="divide-y divide-border">
                    {allWebhooks.length === 0 ? (
                        <div className="px-4 py-12 text-center text-sm text-muted-foreground">
                            <Globe className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
                            No webhook endpoints configured yet.
                        </div>
                    ) : (
                        allWebhooks.map((wh) => (
                            <div
                                key={wh.id}
                                className="flex items-center justify-between px-4 py-3 hover:bg-secondary/50 transition-colors"
                            >
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2">
                                        <p className="truncate text-sm font-mono text-foreground max-w-md">
                                            {wh.url}
                                        </p>
                                        <button
                                            onClick={() => copyUrl(wh)}
                                            className="shrink-0 rounded p-1 text-muted-foreground hover:text-foreground transition-colors"
                                            title="Copy URL"
                                        >
                                            {copiedId === wh.id ? (
                                                <Check className="h-3.5 w-3.5 text-emerald-500" />
                                            ) : (
                                                <Copy className="h-3.5 w-3.5" />
                                            )}
                                        </button>
                                    </div>
                                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                                        {wh.events.map((ev) => (
                                            <span
                                                key={ev}
                                                className="rounded bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400"
                                            >
                                                {ev}
                                            </span>
                                        ))}
                                        <span className="text-xs text-muted-foreground">
                                            · Created {timeAgo(wh.created_at)}
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 shrink-0 ml-4">
                                    <span
                                        className={cn(
                                            "rounded-full px-2 py-0.5 text-[10px] font-medium",
                                            wh.is_active
                                                ? "bg-low/15 text-low"
                                                : "bg-muted text-muted-foreground"
                                        )}
                                    >
                                        {wh.is_active ? "Active" : "Disabled"}
                                    </span>
                                    <button
                                        onClick={() => handleTest(wh.id)}
                                        className="rounded p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                                        title="Send test event"
                                    >
                                        <TestTube className="h-3.5 w-3.5" />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(wh.id)}
                                        className="rounded p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Create Modal */}
            {showCreate && (
                <CreateWebhookModal onClose={() => setShowCreate(false)} />
            )}
        </div>
    );
}

function CreateWebhookModal({ onClose }: { onClose: () => void }) {
    const [url, setUrl] = useState("");
    const [secret, setSecret] = useState("");
    const [selectedEvents, setSelectedEvents] = useState<string[]>([
        "attack.completed",
        "attack.failed",
    ]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    function toggleEvent(event: string) {
        setSelectedEvents((prev) =>
            prev.includes(event)
                ? prev.filter((e) => e !== event)
                : [...prev, event]
        );
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        if (selectedEvents.length === 0) {
            setError("Select at least one event");
            return;
        }
        setLoading(true);
        try {
            await api.post("/webhooks", {
                url,
                events: selectedEvents,
                secret: secret || undefined,
                is_active: true,
            });
            mutate("/webhooks");
            onClose();
        } catch {
            setError("Failed to create webhook");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-foreground">
                        Add Webhook Endpoint
                    </h3>
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
                        <label className="text-sm font-medium text-foreground">
                            Endpoint URL
                        </label>
                        <input
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            required
                            type="url"
                            placeholder="https://your-server.com/webhook"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">
                            Secret (optional)
                        </label>
                        <input
                            value={secret}
                            onChange={(e) => setSecret(e.target.value)}
                            type="password"
                            placeholder="HMAC signing secret"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                        <p className="text-xs text-muted-foreground">
                            Used to sign payloads with HMAC-SHA256
                        </p>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                            Events
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                            {AVAILABLE_EVENTS.map((ev) => (
                                <label
                                    key={ev}
                                    className={cn(
                                        "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                                        selectedEvents.includes(ev)
                                            ? "border-primary bg-primary/10 text-primary"
                                            : "border-border text-muted-foreground hover:bg-secondary"
                                    )}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedEvents.includes(ev)}
                                        onChange={() => toggleEvent(ev)}
                                        className="sr-only"
                                    />
                                    <span
                                        className={cn(
                                            "flex h-4 w-4 items-center justify-center rounded border",
                                            selectedEvents.includes(ev)
                                                ? "border-primary bg-primary text-primary-foreground"
                                                : "border-border"
                                        )}
                                    >
                                        {selectedEvents.includes(ev) && (
                                            <Check className="h-3 w-3" />
                                        )}
                                    </span>
                                    {ev}
                                </label>
                            ))}
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {loading ? "Creating..." : "Create Webhook"}
                    </button>
                </form>
            </div>
        </div>
    );
}
