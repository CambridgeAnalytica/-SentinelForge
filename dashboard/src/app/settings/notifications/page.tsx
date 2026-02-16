"use client";

import { useState } from "react";
import { useWebhooks, useNotificationChannels } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";
import {
    Bell,
    Plus,
    Trash2,
    TestTube,
    X,
    Globe,
    Mail,
    MessageSquare,
    Hash,
} from "lucide-react";
import { mutate } from "swr";

const CHANNEL_ICONS: Record<string, React.ElementType> = {
    webhook: Globe,
    slack: Hash,
    email: Mail,
    teams: MessageSquare,
};

export default function NotificationsPage() {
    const { data: channels, isLoading: chLoading } = useNotificationChannels();
    const { data: webhooks, isLoading: whLoading } = useWebhooks();
    const [showCreate, setShowCreate] = useState(false);

    const loading = chLoading || whLoading;

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    const allChannels = channels ?? [];
    const allWebhooks = webhooks ?? [];

    async function handleTest(id: string) {
        try {
            await api.post(`/notifications/channels/${id}/test`);
        } catch {
            // silent
        }
    }

    async function handleDeleteChannel(id: string) {
        if (!confirm("Delete this channel?")) return;
        await api.delete(`/notifications/channels/${id}`);
        mutate("/notifications/channels");
    }

    async function handleDeleteWebhook(id: string) {
        if (!confirm("Delete this webhook?")) return;
        await api.delete(`/webhooks/${id}`);
        mutate("/webhooks");
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">
                        Notifications & Webhooks
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Configure where scan results and alerts are sent
                    </p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> Add Channel
                </button>
            </div>

            {/* Notification channels */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">
                        Notification Channels
                    </h3>
                </div>
                <div className="divide-y divide-border">
                    {allChannels.length === 0 ? (
                        <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                            <Bell className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
                            No notification channels configured.
                        </div>
                    ) : (
                        allChannels.map((ch) => {
                            const Icon = CHANNEL_ICONS[ch.type] ?? Globe;
                            return (
                                <div
                                    key={ch.id}
                                    className="flex items-center justify-between px-4 py-3 hover:bg-secondary/50 transition-colors"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-secondary">
                                            <Icon className="h-4 w-4 text-muted-foreground" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-foreground">
                                                {ch.name}
                                            </p>
                                            <p className="text-xs text-muted-foreground capitalize">
                                                {ch.type} · Created {timeAgo(ch.created_at)}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={cn(
                                                "rounded-full px-2 py-0.5 text-[10px] font-medium",
                                                ch.is_active
                                                    ? "bg-low/15 text-low"
                                                    : "bg-muted text-muted-foreground"
                                            )}
                                        >
                                            {ch.is_active ? "Active" : "Paused"}
                                        </span>
                                        <button
                                            onClick={() => handleTest(ch.id)}
                                            className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                                            title="Send test"
                                        >
                                            <TestTube className="h-3.5 w-3.5" />
                                        </button>
                                        <button
                                            onClick={() => handleDeleteChannel(ch.id)}
                                            className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                            title="Delete"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Webhooks */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">Webhooks</h3>
                </div>
                <div className="divide-y divide-border">
                    {allWebhooks.length === 0 ? (
                        <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                            No webhooks configured.
                        </div>
                    ) : (
                        allWebhooks.map((wh) => (
                            <div
                                key={wh.id}
                                className="flex items-center justify-between px-4 py-3 hover:bg-secondary/50 transition-colors"
                            >
                                <div>
                                    <p className="text-sm font-mono text-foreground truncate max-w-md">
                                        {wh.url}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        Events: {wh.events.join(", ")}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2">
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
                                        onClick={() => handleDeleteWebhook(wh.id)}
                                        className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Create modal */}
            {showCreate && (
                <CreateChannelModal onClose={() => setShowCreate(false)} />
            )}
        </div>
    );
}

function CreateChannelModal({ onClose }: { onClose: () => void }) {
    const [name, setName] = useState("");
    const [type, setType] = useState("slack");
    const [configValue, setConfigValue] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const configLabel: Record<string, string> = {
        slack: "Webhook URL",
        webhook: "Endpoint URL",
        email: "Email Address",
        teams: "Webhook URL",
    };

    const configKey: Record<string, string> = {
        slack: "webhook_url",
        webhook: "url",
        email: "to_address",
        teams: "webhook_url",
    };

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await api.post("/notifications/channels", {
                name,
                type,
                config: { [configKey[type] ?? "url"]: configValue },
                is_active: true,
            });
            mutate("/notifications/channels");
            onClose();
        } catch {
            setError("Failed to create channel");
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
                        Add Notification Channel
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
                        <label className="text-sm font-medium text-foreground">Name</label>
                        <input
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            placeholder="my-slack-alerts"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </div>

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">Type</label>
                        <select
                            value={type}
                            onChange={(e) => setType(e.target.value)}
                            className="h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                            <option value="slack">Slack</option>
                            <option value="teams">Microsoft Teams</option>
                            <option value="email">Email</option>
                            <option value="webhook">Webhook</option>
                        </select>
                    </div>

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">
                            {configLabel[type] ?? "URL"}
                        </label>
                        <input
                            value={configValue}
                            onChange={(e) => setConfigValue(e.target.value)}
                            required
                            placeholder={
                                type === "email"
                                    ? "security@company.com"
                                    : "https://hooks.slack.com/..."
                            }
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {loading ? "Creating..." : "Create Channel"}
                    </button>
                </form>
            </div>
        </div>
    );
}
