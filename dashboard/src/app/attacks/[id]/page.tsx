"use client";

import { useAttackRunDetail, useAttackRunSSE, type Finding } from "@/hooks/use-api";
import { cn, severityBadge, statusColor, timeAgo, capitalize } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
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
    FileText,
    Download,
    Loader2,
    Trash2,
    ShieldCheck,
    Copy,
    Table,
} from "lucide-react";
import { useState, useEffect } from "react";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export default function AttackRunDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const isAdmin = user?.role === "admin";
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

    async function handleToggleFP(findingId: string) {
        try {
            await api.patch(`/attacks/findings/${findingId}/false-positive`);
            mutate();
        } catch {
            alert("Failed to toggle false positive status.");
        }
    }

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
                {/* Report + export + harden + delete buttons */}
                <div className="flex items-center gap-2 shrink-0">
                    {run.status === "completed" && (
                        <>
                            <ReportButtons runId={run.id} />
                            <CsvExportButton runId={run.id} />
                            {(run.findings?.length ?? 0) > 0 && (
                                <HardenButton runId={run.id} />
                            )}
                        </>
                    )}
                    {isAdmin && (
                        <DeleteButton runId={run.id} onDeleted={() => router.push("/")} />
                    )}
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

            {/* Stats row — exclude false positives from counts */}
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <MiniStat
                    icon={Shield}
                    label="Active Findings"
                    value={findings.filter((f) => !f.false_positive).length}
                    color="text-primary"
                />
                <MiniStat
                    icon={AlertTriangle}
                    label="Critical / High"
                    value={
                        findings.filter((f) => !f.false_positive && (f.severity === "critical" || f.severity === "high")).length
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
                            <FindingRow key={f.id} finding={f} onToggleFP={isAdmin ? handleToggleFP : undefined} />
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

function FindingRow({ finding, onToggleFP }: { finding: Finding; onToggleFP?: (id: string) => void }) {
    const [open, setOpen] = useState(false);
    const isFP = finding.false_positive;
    return (
        <div className={cn(isFP && "opacity-50")}>
            <button
                onClick={() => setOpen(!open)}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-secondary/50 transition-colors"
            >
                <span
                    className={cn(
                        "shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                        isFP ? "bg-zinc-700/50 text-zinc-500 line-through" : severityBadge(finding.severity)
                    )}
                >
                    {isFP ? "FP" : finding.severity?.toUpperCase()}
                </span>
                <span className={cn("flex-1 text-sm font-medium truncate", isFP ? "text-muted-foreground line-through" : "text-foreground")}>
                    {finding.title}
                </span>
                {isFP && (
                    <span className="shrink-0 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                        FALSE POSITIVE
                    </span>
                )}
                {!isFP && finding.is_new !== undefined && (
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
                            <pre className="mt-1 whitespace-pre-wrap break-words rounded-lg bg-background p-2 text-xs text-muted-foreground">
                                {JSON.stringify(finding.evidence, null, 2)}
                            </pre>
                        </div>
                    )}
                    {onToggleFP && (
                        <button
                            onClick={(e) => { e.stopPropagation(); onToggleFP(finding.id); }}
                            className={cn(
                                "mt-2 flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                                isFP
                                    ? "border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                                    : "border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
                            )}
                        >
                            {isFP ? "Restore Finding" : "Mark as False Positive"}
                        </button>
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
            <pre className="whitespace-pre-wrap break-words rounded-lg bg-secondary/50 p-3 text-xs text-muted-foreground">
                {JSON.stringify(data, null, 2)}
            </pre>
        </div>
    );
}

function ReportButtons({ runId }: { runId: string }) {
    const [generating, setGenerating] = useState<string | null>(null);

    async function generate(format: "html" | "pdf") {
        setGenerating(format);
        try {
            const reports = await api.post<{ id: string; format: string }[]>(
                "/reports/generate",
                { run_id: runId, formats: [format] }
            );
            if (reports?.[0]?.id) {
                // Open the report view/download in a new tab
                const token = localStorage.getItem("sf_token");
                const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
                const endpoint = format === "pdf" ? "download" : "view";
                const url = `${base}/reports/${reports[0].id}/${endpoint}${token ? `?token=${token}` : ""}`;
                window.open(url, "_blank");
            }
        } catch {
            // Fallback: try inline generation via view endpoint
            alert("Report generation failed. Check API logs.");
        } finally {
            setGenerating(null);
        }
    }

    return (
        <div className="flex gap-2 shrink-0">
            <button
                onClick={() => generate("html")}
                disabled={generating !== null}
                className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-secondary disabled:opacity-50"
            >
                {generating === "html" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                    <FileText className="h-3.5 w-3.5" />
                )}
                HTML Report
            </button>
            <button
                onClick={() => generate("pdf")}
                disabled={generating !== null}
                className="flex h-8 items-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
                {generating === "pdf" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                    <Download className="h-3.5 w-3.5" />
                )}
                PDF Report
            </button>
        </div>
    );
}

function CsvExportButton({ runId }: { runId: string }) {
    function handleExport() {
        const token = localStorage.getItem("sf_token");
        const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        const url = `${base}/attacks/runs/${runId}/export?format=csv${token ? `&token=${token}` : ""}`;
        window.open(url, "_blank");
    }

    return (
        <button
            onClick={handleExport}
            className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
            title="Export findings as CSV"
        >
            <Table className="h-3.5 w-3.5" />
            CSV
        </button>
    );
}

function HardenButton({ runId }: { runId: string }) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [advice, setAdvice] = useState<{
        recommendations: { category: string; priority: string; recommendation: string; system_prompt_snippet: string; test_types_failed: string[] }[];
        hardened_system_prompt: string;
        total_failed_tests: number;
    } | null>(null);

    async function loadAdvice() {
        if (advice) {
            setOpen(!open);
            return;
        }
        setLoading(true);
        try {
            const resp = await api.get<typeof advice>(`/attacks/runs/${runId}/harden`);
            setAdvice(resp);
            setOpen(true);
        } catch {
            alert("Failed to load hardening advice.");
        } finally {
            setLoading(false);
        }
    }

    function copySnippet(text: string) {
        navigator.clipboard.writeText(text);
    }

    const priorityColor: Record<string, string> = {
        critical: "bg-red-500/20 text-red-400",
        high: "bg-orange-500/20 text-orange-400",
        medium: "bg-yellow-500/20 text-yellow-400",
    };

    return (
        <>
            <button
                onClick={loadAdvice}
                disabled={loading}
                className="flex h-8 items-center gap-1.5 rounded-md border border-emerald-500/30 bg-card px-3 text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-500/10"
                title="System prompt hardening advisor"
            >
                {loading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                    <ShieldCheck className="h-3.5 w-3.5" />
                )}
                Harden
            </button>
            {open && advice && (
                <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 pt-16 overflow-y-auto">
                    <div className="w-full max-w-2xl rounded-xl border border-border bg-card shadow-xl">
                        <div className="flex items-center justify-between border-b border-border px-4 py-3">
                            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                                Hardening Advisor — {advice.total_failed_tests} failed tests
                            </h3>
                            <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground text-lg">&times;</button>
                        </div>
                        <div className="max-h-[70vh] overflow-y-auto p-4 space-y-3">
                            {advice.recommendations.map((rec, i) => (
                                <div key={i} className="rounded-lg border border-border p-3">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase", priorityColor[rec.priority] ?? "bg-zinc-500/20 text-zinc-400")}>
                                            {rec.priority}
                                        </span>
                                        <span className="text-sm font-medium text-foreground">{rec.category}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground mb-2">{rec.recommendation}</p>
                                    <div className="relative">
                                        <pre className="whitespace-pre-wrap break-words rounded-lg bg-secondary/50 p-2 text-xs text-foreground/80">{rec.system_prompt_snippet}</pre>
                                        <button
                                            onClick={() => copySnippet(rec.system_prompt_snippet)}
                                            className="absolute top-1 right-1 rounded p-1 text-muted-foreground hover:text-foreground hover:bg-secondary"
                                            title="Copy snippet"
                                        >
                                            <Copy className="h-3 w-3" />
                                        </button>
                                    </div>
                                    {rec.test_types_failed.length > 0 && (
                                        <div className="mt-1 flex flex-wrap gap-1">
                                            {rec.test_types_failed.map((t) => (
                                                <span key={t} className="rounded bg-secondary px-1.5 py-0.5 text-[9px] text-muted-foreground">{t}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                            {/* Full hardened prompt */}
                            <div className="rounded-lg border border-emerald-500/20 p-3">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-semibold text-foreground">Complete Hardened System Prompt</span>
                                    <button
                                        onClick={() => copySnippet(advice.hardened_system_prompt)}
                                        className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-secondary"
                                    >
                                        <Copy className="h-3 w-3" /> Copy All
                                    </button>
                                </div>
                                <pre className="whitespace-pre-wrap break-words rounded-lg bg-secondary/50 p-3 text-xs text-foreground/80 max-h-64 overflow-y-auto">{advice.hardened_system_prompt}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

function DeleteButton({ runId, onDeleted }: { runId: string; onDeleted: () => void }) {
    const [confirming, setConfirming] = useState(false);
    const [deleting, setDeleting] = useState(false);

    async function handleDelete() {
        setDeleting(true);
        try {
            await api.delete(`/attacks/runs/${runId}`);
            onDeleted();
        } catch {
            alert("Failed to delete scan run.");
        } finally {
            setDeleting(false);
            setConfirming(false);
        }
    }

    if (confirming) {
        return (
            <div className="flex items-center gap-1.5">
                <span className="text-xs text-muted-foreground">Delete?</span>
                <button
                    onClick={handleDelete}
                    disabled={deleting}
                    className="flex h-8 items-center gap-1.5 rounded-md bg-destructive px-3 text-xs font-medium text-destructive-foreground transition-colors hover:bg-destructive/90 disabled:opacity-50"
                >
                    {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Yes, delete"}
                </button>
                <button
                    onClick={() => setConfirming(false)}
                    className="flex h-8 items-center rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
                >
                    Cancel
                </button>
            </div>
        );
    }

    return (
        <button
            onClick={() => setConfirming(true)}
            className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
            title="Delete this scan"
        >
            <Trash2 className="h-3.5 w-3.5" />
        </button>
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
