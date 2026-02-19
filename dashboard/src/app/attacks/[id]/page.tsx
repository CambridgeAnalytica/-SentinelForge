"use client";

import { useAttackRunDetail, useAttackRunSSE, type Finding } from "@/hooks/use-api";
import { cn, severityBadge, statusColor, timeAgo, capitalize } from "@/lib/utils";
import { useParams, useRouter } from "next/navigation";
import {
    ArrowLeft,
    Activity,
    AlertTriangle,
    CheckCircle2,
    Clock,
    XCircle,
    Link2,
    ChevronDown,
    ChevronUp,
    Shield,
    Radio,
} from "lucide-react";
import { useState, useEffect } from "react";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export default function AttackRunDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = typeof params.id === "string" ? params.id : null;
    const { data: run, isLoading, error, mutate } = useAttackRunDetail(id);

    // SSE live progress — only connect when run is active
    const isActive = run?.status === "running" || run?.status === "queued";
    const { progress: sseProgress, connected: sseConnected } = useAttackRunSSE(
        isActive ? id : null
    );

    // When SSE signals completion, refresh full data from API
    useEffect(() => {
        if (sseProgress && (sseProgress.status === "completed" || sseProgress.status === "failed")) {
            mutate();
        }
    }, [sseProgress?.status, mutate]);

    // Use SSE progress when available, fall back to SWR data
    const liveProgress = sseProgress?.progress ?? run?.progress ?? 0;
    const liveStatus = sseProgress?.status ?? run?.status;

    if (isLoading) return <PageSkeleton />;
    if (error || !run) {
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-24 text-muted-foreground">
                <XCircle className="h-10 w-10" />
                <p>Attack run not found</p>
                <button
                    onClick={() => router.push("/")}
                    className="text-sm text-primary hover:underline"
                >
                    ← Back to dashboard
                </button>
            </div>
        );
    }

    const findings = run.findings ?? [];
    const sorted = [...findings].sort(
        (a, b) =>
            SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
    );

    return (
        <div className="space-y-6">
            {/* Back nav + header */}
            <div className="flex items-start gap-4">
                <button
                    onClick={() => router.push("/")}
                    className="mt-1 rounded-lg p-1.5 text-muted-foreground hover:bg-secondary transition-colors"
                >
                    <ArrowLeft className="h-5 w-5" />
                </button>
                <div className="flex-1">
                    <div className="flex items-center gap-3">
                        <h2 className="text-2xl font-bold text-foreground">
                            {run.scenario_id}
                        </h2>
                        <StatusBadge status={liveStatus ?? run.status} />
                        {sseConnected && (
                            <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-400">
                                <span className="relative flex h-2 w-2">
                                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                                </span>
                                LIVE
                            </span>
                        )}
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Target: <span className="font-medium text-foreground">{run.target_model}</span>
                        {run.started_at && <> · Started {timeAgo(run.started_at)}</>}
                    </p>
                </div>
            </div>

            {/* Progress bar for running attacks — driven by SSE when connected */}
            {isActive && (
                <div className="rounded-xl border border-border bg-card p-4">
                    <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2 text-muted-foreground">
                            <Clock className="h-4 w-4 animate-spin" />
                            {liveStatus === "queued" ? "Waiting in queue…" : "Scan in progress…"}
                        </span>
                        <span className="font-mono text-foreground">
                            {Math.round(liveProgress * 100)}%
                        </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-secondary">
                        <div
                            className="h-full rounded-full bg-gradient-to-r from-primary to-info transition-all duration-300"
                            style={{ width: `${Math.max(liveProgress * 100, 2)}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Stats row */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <MiniStat
                    icon={Shield}
                    label="Total Findings"
                    value={findings.length}
                    color="text-primary"
                />
                <MiniStat
                    icon={AlertTriangle}
                    label="Critical / High"
                    value={
                        findings.filter((f) => f.severity === "critical" || f.severity === "high").length
                    }
                    color="text-critical"
                />
                <MiniStat
                    icon={Activity}
                    label="Tools Used"
                    value={new Set(findings.map((f) => f.tool_name)).size}
                    color="text-info"
                />
                <MiniStat
                    icon={CheckCircle2}
                    label="MITRE Techniques"
                    value={new Set(findings.filter((f) => f.mitre_technique).map((f) => f.mitre_technique)).size}
                    color="text-warning"
                />
            </div>

            {/* Error message */}
            {run.error_message && (
                <div className="rounded-xl border border-critical/30 bg-critical/10 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-critical">
                        <XCircle className="h-4 w-4" />
                        Error
                    </div>
                    <p className="mt-1 text-sm text-foreground/80">{run.error_message}</p>
                </div>
            )}

            {/* Findings table */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">
                        Findings ({findings.length})
                    </h3>
                </div>
                {sorted.length === 0 ? (
                    <div className="px-4 py-12 text-center text-sm text-muted-foreground">
                        {isActive
                            ? "Findings will appear here as the scan progresses…"
                            : "No findings — this target passed all tests."}
                    </div>
                ) : (
                    <div className="divide-y divide-border">
                        {sorted.map((f) => (
                            <FindingRow key={f.id} finding={f} />
                        ))}
                    </div>
                )}
            </div>

            {/* Evidence chain */}
            {findings.some((f) => f.evidence_hash) && (
                <div className="rounded-xl border border-border bg-card p-4">
                    <h3 className="mb-3 text-sm font-semibold text-foreground flex items-center gap-2">
                        <Link2 className="h-4 w-4" />
                        Evidence Chain
                    </h3>
                    <div className="space-y-2">
                        {sorted
                            .filter((f) => f.evidence_hash)
                            .map((f, i) => (
                                <div
                                    key={f.id}
                                    className="flex items-center gap-3 text-xs font-mono text-muted-foreground"
                                >
                                    <span className="w-6 text-center text-foreground font-bold">
                                        {i + 1}
                                    </span>
                                    <div className="flex-1 rounded-lg border border-border bg-secondary/50 p-2">
                                        <span className="text-foreground">{f.title}</span>
                                        <div className="mt-1 flex gap-4">
                                            <span>hash: {f.evidence_hash?.slice(0, 16)}…</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                    </div>
                </div>
            )}

            {/* Config & Results */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {run.config && Object.keys(run.config).length > 0 && (
                    <JsonBlock title="Configuration" data={run.config} />
                )}
                {run.results && Object.keys(run.results).length > 0 && (
                    <JsonBlock title="Results" data={run.results} />
                )}
            </div>
        </div>
    );
}

/* ── Sub-components ── */

function StatusBadge({ status }: { status: string }) {
    const icons: Record<string, typeof Activity> = {
        running: Clock,
        completed: CheckCircle2,
        failed: XCircle,
        queued: Clock,
    };
    const Icon = icons[status] ?? Activity;
    return (
        <span
            className={cn(
                "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                statusColor(status)
            )}
        >
            <Icon className={cn("h-3 w-3", status === "running" && "animate-spin")} />
            {capitalize(status)}
        </span>
    );
}

function MiniStat({
    icon: Icon,
    label,
    value,
    color,
}: {
    icon: typeof Activity;
    label: string;
    value: number;
    color: string;
}) {
    return (
        <div className="rounded-xl border border-border bg-card p-3">
            <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{label}</span>
                <Icon className={cn("h-4 w-4", color)} />
            </div>
            <p className="mt-1 text-xl font-bold text-foreground">{value}</p>
        </div>
    );
}

function FindingRow({ finding }: { finding: Finding }) {
    const [open, setOpen] = useState(false);
    return (
        <div>
            <button
                onClick={() => setOpen(!open)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-secondary/50 transition-colors"
            >
                <span
                    className={cn(
                        "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                        severityBadge(finding.severity)
                    )}
                >
                    {finding.severity?.toUpperCase()}
                </span>
                <span className="flex-1 text-sm font-medium text-foreground truncate">
                    {finding.title}
                </span>
                {finding.is_new !== undefined && (
                    <span
                        className={cn(
                            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold",
                            finding.is_new
                                ? "bg-emerald-500/20 text-emerald-400"
                                : "bg-zinc-700/50 text-zinc-400"
                        )}
                    >
                        {finding.is_new ? "NEW" : "RECURRING"}
                    </span>
                )}
                <span className="shrink-0 text-xs text-muted-foreground">
                    {finding.tool_name}
                </span>
                {finding.mitre_technique && (
                    <span className="shrink-0 rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        {finding.mitre_technique}
                    </span>
                )}
                {open ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
            </button>
            {open && (
                <div className="border-t border-border bg-secondary/30 px-4 py-3 space-y-2">
                    {finding.description && (
                        <p className="text-sm text-foreground/80">{finding.description}</p>
                    )}
                    {finding.remediation && (
                        <div>
                            <span className="text-xs font-semibold text-muted-foreground">
                                Remediation
                            </span>
                            <p className="text-sm text-foreground/80">{finding.remediation}</p>
                        </div>
                    )}
                    {finding.evidence && Object.keys(finding.evidence).length > 0 && (
                        <div>
                            <span className="text-xs font-semibold text-muted-foreground">
                                Evidence
                            </span>
                            <pre className="mt-1 overflow-x-auto rounded-lg bg-background p-2 text-xs text-muted-foreground">
                                {JSON.stringify(finding.evidence, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function JsonBlock({
    title,
    data,
}: {
    title: string;
    data: Record<string, unknown>;
}) {
    return (
        <div className="rounded-xl border border-border bg-card p-4">
            <h3 className="mb-2 text-sm font-semibold text-foreground">{title}</h3>
            <pre className="overflow-x-auto rounded-lg bg-secondary/50 p-3 text-xs text-muted-foreground">
                {JSON.stringify(data, null, 2)}
            </pre>
        </div>
    );
}

function PageSkeleton() {
    return (
        <div className="space-y-6">
            <div className="h-8 w-64 animate-pulse rounded bg-secondary" />
            <div className="h-4 w-48 animate-pulse rounded bg-secondary" />
            <div className="grid grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-20 animate-pulse rounded-xl bg-secondary" />
                ))}
            </div>
            <div className="h-64 animate-pulse rounded-xl bg-secondary" />
        </div>
    );
}
