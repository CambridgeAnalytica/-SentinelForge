"use client";

import { useState } from "react";
import { useSchedules } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { capitalize, timeAgo, cn } from "@/lib/utils";
import { Calendar, Plus, Play, Trash2, X } from "lucide-react";
import { mutate } from "swr";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function SchedulesPage() {
    const { data: schedules, isLoading } = useSchedules();
    const [showCreate, setShowCreate] = useState(false);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    const allSchedules = schedules ?? [];

    async function handleTrigger(id: string) {
        await api.post(`/schedules/${id}/trigger`);
        mutate("/schedules");
    }

    async function handleDelete(id: string) {
        if (!confirm("Delete this schedule?")) return;
        await api.delete(`/schedules/${id}`);
        mutate("/schedules");
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">
                        Schedule Manager
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Create and manage recurring security scans
                    </p>
                </div>
                <button
                    onClick={() => setShowCreate(true)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> New Schedule
                </button>
            </div>

            {/* Schedule table */}
            <div className="rounded-xl border border-border bg-card">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                <th className="px-4 py-2 font-medium">Name</th>
                                <th className="px-4 py-2 font-medium">Scenario</th>
                                <th className="px-4 py-2 font-medium">Target</th>
                                <th className="px-4 py-2 font-medium">Cron</th>
                                <th className="px-4 py-2 font-medium">Next Run</th>
                                <th className="px-4 py-2 font-medium">Status</th>
                                <th className="px-4 py-2 font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {allSchedules.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={7}
                                        className="px-4 py-12 text-center text-muted-foreground"
                                    >
                                        <Calendar className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
                                        No schedules set up yet.
                                    </td>
                                </tr>
                            ) : (
                                allSchedules.map((s) => (
                                    <tr
                                        key={s.id}
                                        className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors"
                                    >
                                        <td className="px-4 py-2.5 font-medium text-foreground">
                                            {s.name}
                                        </td>
                                        <td className="px-4 py-2.5 text-muted-foreground">
                                            {s.scenario_id}
                                        </td>
                                        <td className="px-4 py-2.5 text-muted-foreground">
                                            {s.target_model}
                                        </td>
                                        <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">
                                            {s.cron_expression}
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                            {s.next_run_at ? timeAgo(s.next_run_at) : "—"}
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <span
                                                className={cn(
                                                    "rounded-full px-2 py-0.5 text-xs font-medium",
                                                    s.is_active
                                                        ? "bg-low/15 text-low"
                                                        : "bg-muted text-muted-foreground"
                                                )}
                                            >
                                                {s.is_active ? "Active" : "Paused"}
                                            </span>
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <div className="flex gap-1">
                                                <button
                                                    onClick={() => handleTrigger(s.id)}
                                                    className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                                                    title="Trigger now"
                                                >
                                                    <Play className="h-3.5 w-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(s.id)}
                                                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                                    title="Delete"
                                                >
                                                    <Trash2 className="h-3.5 w-3.5" />
                                                </button>
                                            </div>
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
                <CreateScheduleModal onClose={() => setShowCreate(false)} />
            )}
        </div>
    );
}

function CreateScheduleModal({ onClose }: { onClose: () => void }) {
    const [name, setName] = useState("");
    const [scenarioId, setScenarioId] = useState("");
    const [targetModel, setTargetModel] = useState("");
    const [minute, setMinute] = useState("0");
    const [hour, setHour] = useState("6");
    const [dayOfWeek, setDayOfWeek] = useState("1");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const cronExpression = `${minute} ${hour} * * ${dayOfWeek}`;

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await api.post("/schedules", {
                name,
                scenario_id: scenarioId,
                target_model: targetModel,
                cron_expression: cronExpression,
                is_active: true,
            });
            mutate("/schedules");
            onClose();
        } catch {
            setError("Failed to create schedule");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-foreground">New Schedule</h3>
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

                    <Field label="Name">
                        <input
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                            placeholder="Weekly injection scan"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </Field>

                    <Field label="Scenario ID">
                        <input
                            value={scenarioId}
                            onChange={(e) => setScenarioId(e.target.value)}
                            required
                            placeholder="prompt_injection"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </Field>

                    <Field label="Target Model">
                        <input
                            value={targetModel}
                            onChange={(e) => setTargetModel(e.target.value)}
                            required
                            placeholder="gpt-4"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </Field>

                    {/* Visual cron builder */}
                    <div className="space-y-3">
                        <label className="text-sm font-medium text-foreground">
                            Schedule
                        </label>
                        <div className="grid grid-cols-3 gap-2">
                            <div>
                                <label className="text-xs text-muted-foreground">Day</label>
                                <select
                                    value={dayOfWeek}
                                    onChange={(e) => setDayOfWeek(e.target.value)}
                                    className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm text-foreground"
                                >
                                    <option value="*">Every day</option>
                                    {DAYS.map((d, i) => (
                                        <option key={d} value={String(i)}>
                                            {d}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Hour</label>
                                <select
                                    value={hour}
                                    onChange={(e) => setHour(e.target.value)}
                                    className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm text-foreground"
                                >
                                    {HOURS.map((h) => (
                                        <option key={h} value={String(h)}>
                                            {String(h).padStart(2, "0")}:00
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="text-xs text-muted-foreground">Minute</label>
                                <select
                                    value={minute}
                                    onChange={(e) => setMinute(e.target.value)}
                                    className="mt-1 h-9 w-full rounded-md border border-input bg-secondary px-2 text-sm text-foreground"
                                >
                                    {[0, 15, 30, 45].map((m) => (
                                        <option key={m} value={String(m)}>
                                            :{String(m).padStart(2, "0")}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <p className="font-mono text-xs text-muted-foreground">
                            Cron: <span className="text-foreground">{cronExpression}</span>
                        </p>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {loading ? "Creating..." : "Create Schedule"}
                    </button>
                </form>
            </div>
        </div>
    );
}

function Field({
    label,
    children,
}: {
    label: string;
    children: React.ReactNode;
}) {
    return (
        <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">{label}</label>
            {children}
        </div>
    );
}
