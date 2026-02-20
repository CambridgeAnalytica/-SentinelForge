"use client";

import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import { cn, capitalize } from "@/lib/utils";
import {
    ArrowLeft,
    CheckCircle2,
    Clock,
    XCircle,
    Shield,
    AlertTriangle,
    Download,
    Table,
} from "lucide-react";

interface AuditDetail {
    id: string;
    target_model: string;
    status: string;
    scenario_count: number;
    completed_count: number;
    posture_score: number | null;
    total_findings: number;
    total_critical: number;
    total_high: number;
    scenarios: {
        run_id: string;
        scenario_id: string;
        status: string;
        progress: number;
        pass_rate: number | null;
        findings_count: number;
        severity_breakdown: Record<string, number>;
        completed_at: string | null;
    }[];
    created_at: string;
}

export default function AuditDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = typeof params.id === "string" ? params.id : null;
    const { data: audit, isLoading } = useSWR<AuditDetail>(
        id ? `/attacks/audits/${id}` : null,
        (p: string) => apiFetch<AuditDetail>(p),
        { refreshInterval: (data) => (data?.status === "running" ? 5000 : 0) }
    );

    if (isLoading) {
        return (
            <div className="space-y-6">
                <div className="h-8 w-64 animate-pulse rounded bg-secondary" />
                <div className="grid grid-cols-4 gap-4">
                    {[...Array(4)].map((_, i) => (
                        <div key={i} className="h-20 animate-pulse rounded-xl bg-secondary" />
                    ))}
                </div>
                <div className="h-64 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    if (!audit) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-24 text-muted-foreground">
                <XCircle className="h-10 w-10" />
                <p>Audit not found</p>
                <button onClick={() => router.push("/")} className="text-sm text-primary hover:underline">
                    Back to dashboard
                </button>
            </div>
        );
    }

    const isRunning = audit.status === "running";
    const completedPct = audit.scenario_count > 0 ? (audit.completed_count / audit.scenario_count) * 100 : 0;

    function handleCsvExport() {
        const token = localStorage.getItem("sf_token");
        const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        window.open(`${base}/attacks/audits/${id}/export?token=${token}`, "_blank");
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start gap-4">
                <button
                    onClick={() => router.push("/")}
                    className="mt-1 rounded-lg p-1.5 text-muted-foreground hover:bg-secondary transition-colors"
                >
                    <ArrowLeft className="h-5 w-5" />
                </button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h2 className="text-2xl font-bold text-foreground">Full Audit</h2>
                        <span className={cn(
                            "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                            audit.status === "completed" ? "bg-emerald-500/20 text-emerald-400" : audit.status === "running" ? "bg-blue-500/20 text-blue-400" : "bg-red-500/20 text-red-400"
                        )}>
                            {audit.status === "running" && <Clock className="h-3 w-3 animate-spin" />}
                            {capitalize(audit.status)}
                        </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Target: <span className="font-medium text-foreground">{audit.target_model}</span>
                        {" · "}{audit.completed_count}/{audit.scenario_count} scenarios
                    </p>
                </div>
                <button
                    onClick={handleCsvExport}
                    className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
                >
                    <Table className="h-3.5 w-3.5" /> Export CSV
                </button>
            </div>

            {/* Progress bar */}
            {isRunning && (
                <div className="rounded-xl border border-border bg-card p-4">
                    <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-4 w-4 animate-spin" />
                            Running {audit.completed_count} of {audit.scenario_count} scenarios...
                        </span>
                        <span className="font-mono text-foreground">{Math.round(completedPct)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-secondary">
                        <div
                            className="h-full rounded-full bg-gradient-to-r from-primary to-info transition-all duration-300"
                            style={{ width: `${Math.max(completedPct, 2)}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Stats cards */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <StatCard
                    icon={Shield}
                    label="Posture Score"
                    value={audit.posture_score != null ? `${audit.posture_score}%` : "—"}
                    color={
                        audit.posture_score != null
                            ? audit.posture_score >= 80 ? "text-low" : audit.posture_score >= 50 ? "text-medium" : "text-critical"
                            : "text-muted-foreground"
                    }
                />
                <StatCard icon={AlertTriangle} label="Total Findings" value={String(audit.total_findings)} color="text-foreground" />
                <StatCard icon={XCircle} label="Critical" value={String(audit.total_critical)} color="text-critical" />
                <StatCard icon={AlertTriangle} label="High" value={String(audit.total_high)} color="text-high" />
            </div>

            {/* Per-scenario results */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">
                        Scenario Results ({audit.scenarios.length})
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                <th className="px-4 py-2 font-medium">Scenario</th>
                                <th className="px-4 py-2 font-medium">Status</th>
                                <th className="px-4 py-2 font-medium">Pass Rate</th>
                                <th className="px-4 py-2 font-medium">Findings</th>
                                <th className="px-4 py-2 font-medium">Critical</th>
                                <th className="px-4 py-2 font-medium">High</th>
                            </tr>
                        </thead>
                        <tbody>
                            {audit.scenarios.map((s) => (
                                <tr
                                    key={s.run_id}
                                    onClick={() => router.push(`/attacks/${s.run_id}`)}
                                    className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors cursor-pointer"
                                >
                                    <td className="px-4 py-2.5 font-medium text-foreground">{s.scenario_id}</td>
                                    <td className="px-4 py-2.5">
                                        <span className={cn(
                                            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                                            s.status === "completed" ? "bg-emerald-500/20 text-emerald-400"
                                                : s.status === "running" ? "bg-blue-500/20 text-blue-400"
                                                    : s.status === "failed" ? "bg-red-500/20 text-red-400"
                                                        : "bg-zinc-500/20 text-zinc-400"
                                        )}>
                                            {s.status === "running" && <Clock className="h-3 w-3 animate-spin" />}
                                            {capitalize(s.status)}
                                        </span>
                                    </td>
                                    <td className="px-4 py-2.5">
                                        {s.pass_rate != null ? (
                                            <div className="flex items-center gap-2">
                                                <div className="h-1.5 w-16 overflow-hidden rounded-full bg-secondary">
                                                    <div
                                                        className={cn(
                                                            "h-full rounded-full",
                                                            s.pass_rate >= 0.8 ? "bg-low" : s.pass_rate >= 0.5 ? "bg-medium" : "bg-critical"
                                                        )}
                                                        style={{ width: `${s.pass_rate * 100}%` }}
                                                    />
                                                </div>
                                                <span className="font-mono text-xs text-foreground">{Math.round(s.pass_rate * 100)}%</span>
                                            </div>
                                        ) : (
                                            <span className="text-muted-foreground">—</span>
                                        )}
                                    </td>
                                    <td className="px-4 py-2.5 font-mono text-foreground">{s.findings_count}</td>
                                    <td className="px-4 py-2.5 font-mono text-critical">{s.severity_breakdown.critical ?? 0}</td>
                                    <td className="px-4 py-2.5 font-mono text-foreground">{s.severity_breakdown.high ?? 0}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function StatCard({
    icon: Icon,
    label,
    value,
    color,
}: {
    icon: typeof Shield;
    label: string;
    value: string;
    color: string;
}) {
    return (
        <div className="rounded-xl border border-border bg-card p-3">
            <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{label}</span>
                <Icon className={cn("h-4 w-4", color)} />
            </div>
            <p className={cn("mt-1 text-xl font-bold", color)}>{value}</p>
        </div>
    );
}
