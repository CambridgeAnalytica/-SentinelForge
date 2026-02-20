"use client";

import { useState } from "react";
import { api, apiFetch } from "@/lib/api";
import { cn, capitalize } from "@/lib/utils";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import {
    GitCompareArrows,
    Plus,
    Trash2,
    Loader2,
    CheckCircle2,
    Clock,
    XCircle,
    AlertTriangle,
} from "lucide-react";

interface Comparison {
    id: string;
    scenario_id: string;
    target_models: string[];
    run_ids: string[];
    status: string;
    created_at: string;
}

interface ComparisonDetail {
    id: string;
    scenario_id: string;
    status: string;
    scorecard: {
        run_id: string;
        target_model: string;
        status: string;
        pass_rate: number | null;
        findings_count: number;
        severity_breakdown: Record<string, number>;
    }[];
}

interface Scenario {
    id: string;
    name: string;
}

export default function ComparePage() {
    const router = useRouter();
    const { data: comparisons, mutate } = useSWR<Comparison[]>(
        "/attacks/comparisons",
        (p: string) => apiFetch<Comparison[]>(p),
        { refreshInterval: 10000 }
    );
    const { data: scenarios } = useSWR<Scenario[]>(
        "/attacks/scenarios",
        (p: string) => apiFetch<Scenario[]>(p)
    );

    const [showForm, setShowForm] = useState(false);
    const [scenarioId, setScenarioId] = useState("");
    const [models, setModels] = useState(["", ""]);
    const [launching, setLaunching] = useState(false);
    const [selectedId, setSelectedId] = useState<string | null>(null);

    const { data: detail } = useSWR<ComparisonDetail>(
        selectedId ? `/attacks/comparisons/${selectedId}` : null,
        (p: string) => apiFetch<ComparisonDetail>(p),
        { refreshInterval: 5000 }
    );

    async function handleLaunch() {
        const validModels = models.filter((m) => m.trim());
        if (!scenarioId || validModels.length < 2) return;
        setLaunching(true);
        try {
            const resp = await api.post<{ id: string }>("/attacks/compare", {
                scenario_id: scenarioId,
                target_models: validModels,
            });
            mutate();
            setSelectedId(resp.id);
            setShowForm(false);
            setModels(["", ""]);
        } catch {
            alert("Failed to launch comparison.");
        } finally {
            setLaunching(false);
        }
    }

    const statusIcon: Record<string, typeof CheckCircle2> = {
        completed: CheckCircle2,
        running: Clock,
        failed: XCircle,
    };

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Model Comparison</h2>
                    <p className="text-sm text-muted-foreground">
                        Run the same scenario against multiple models side-by-side
                    </p>
                </div>
                <button
                    onClick={() => setShowForm(!showForm)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                >
                    <GitCompareArrows className="h-4 w-4" /> New Comparison
                </button>
            </div>

            {/* New comparison form */}
            {showForm && (
                <div className="rounded-xl border border-border bg-card p-4 space-y-3">
                    <div>
                        <label className="text-xs font-medium text-muted-foreground">Scenario</label>
                        <select
                            value={scenarioId}
                            onChange={(e) => setScenarioId(e.target.value)}
                            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                        >
                            <option value="">Select scenario...</option>
                            {(scenarios ?? []).map((s) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="text-xs font-medium text-muted-foreground">Models (2-5)</label>
                        {models.map((m, i) => (
                            <div key={i} className="mt-1 flex gap-2">
                                <input
                                    value={m}
                                    onChange={(e) => {
                                        const next = [...models];
                                        next[i] = e.target.value;
                                        setModels(next);
                                    }}
                                    placeholder={`Model ${i + 1}`}
                                    className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                                />
                                {models.length > 2 && (
                                    <button
                                        onClick={() => setModels(models.filter((_, j) => j !== i))}
                                        className="rounded-md p-2 text-muted-foreground hover:text-destructive"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                )}
                            </div>
                        ))}
                        {models.length < 5 && (
                            <button
                                onClick={() => setModels([...models, ""])}
                                className="mt-2 flex items-center gap-1 text-xs text-primary hover:underline"
                            >
                                <Plus className="h-3 w-3" /> Add model
                            </button>
                        )}
                    </div>
                    <button
                        onClick={handleLaunch}
                        disabled={launching || !scenarioId || models.filter((m) => m.trim()).length < 2}
                        className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                    >
                        {launching && <Loader2 className="h-4 w-4 animate-spin" />}
                        Launch Comparison
                    </button>
                </div>
            )}

            {/* Comparison list */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">Recent Comparisons</h3>
                </div>
                {(comparisons ?? []).length === 0 ? (
                    <div className="px-4 py-12 text-center text-sm text-muted-foreground">
                        No comparisons yet. Create one to compare models side-by-side.
                    </div>
                ) : (
                    <div className="divide-y divide-border">
                        {(comparisons ?? []).map((c) => {
                            const Icon = statusIcon[c.status] ?? Clock;
                            return (
                                <button
                                    key={c.id}
                                    onClick={() => setSelectedId(c.id)}
                                    className={cn(
                                        "flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-secondary/50 transition-colors",
                                        selectedId === c.id && "bg-secondary/50"
                                    )}
                                >
                                    <Icon className={cn("h-4 w-4 shrink-0", c.status === "completed" ? "text-low" : c.status === "running" ? "text-info animate-spin" : "text-critical")} />
                                    <span className="flex-1 text-sm font-medium text-foreground">{c.scenario_id}</span>
                                    <span className="text-xs text-muted-foreground">{c.target_models.join(" vs ")}</span>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Comparison detail / scorecard */}
            {detail && (
                <div className="rounded-xl border border-border bg-card p-4">
                    <h3 className="mb-4 text-sm font-semibold text-foreground flex items-center gap-2">
                        <GitCompareArrows className="h-4 w-4" />
                        Scorecard — {detail.scenario_id}
                        <span className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                            detail.status === "completed" ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400"
                        )}>
                            {capitalize(detail.status)}
                        </span>
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                    <th className="px-3 py-2 font-medium">Model</th>
                                    <th className="px-3 py-2 font-medium">Status</th>
                                    <th className="px-3 py-2 font-medium">Pass Rate</th>
                                    <th className="px-3 py-2 font-medium">Findings</th>
                                    <th className="px-3 py-2 font-medium">Critical</th>
                                    <th className="px-3 py-2 font-medium">High</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detail.scorecard.map((row) => {
                                    const best = detail.scorecard.reduce((a, b) =>
                                        (a.pass_rate ?? 0) > (b.pass_rate ?? 0) ? a : b
                                    );
                                    const isBest = row.run_id === best.run_id && detail.status === "completed";
                                    return (
                                        <tr
                                            key={row.run_id}
                                            onClick={() => router.push(`/attacks/${row.run_id}`)}
                                            className={cn(
                                                "border-b border-border last:border-0 cursor-pointer hover:bg-secondary/50 transition-colors",
                                                isBest && "bg-emerald-500/5"
                                            )}
                                        >
                                            <td className="px-3 py-2 font-medium text-foreground">
                                                {row.target_model}
                                                {isBest && <span className="ml-2 text-[10px] text-emerald-400">BEST</span>}
                                            </td>
                                            <td className="px-3 py-2 text-muted-foreground">{capitalize(row.status)}</td>
                                            <td className="px-3 py-2">
                                                {row.pass_rate != null ? (
                                                    <span className={cn("font-mono", row.pass_rate >= 0.8 ? "text-low" : row.pass_rate >= 0.5 ? "text-medium" : "text-critical")}>
                                                        {Math.round(row.pass_rate * 100)}%
                                                    </span>
                                                ) : (
                                                    <span className="text-muted-foreground">—</span>
                                                )}
                                            </td>
                                            <td className="px-3 py-2 font-mono text-foreground">{row.findings_count}</td>
                                            <td className="px-3 py-2">
                                                {(row.severity_breakdown.critical ?? 0) > 0 ? (
                                                    <span className="flex items-center gap-1 text-critical">
                                                        <AlertTriangle className="h-3 w-3" />
                                                        {row.severity_breakdown.critical}
                                                    </span>
                                                ) : (
                                                    <span className="text-muted-foreground">0</span>
                                                )}
                                            </td>
                                            <td className="px-3 py-2 font-mono text-foreground">{row.severity_breakdown.high ?? 0}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
}
