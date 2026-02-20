"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useRagEvals, useRagEvalDetail } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import {
    FileSearch,
    Play,
    Loader2,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    FileWarning,
} from "lucide-react";

const STATUS_ICON: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-4 w-4 text-green-400" />,
    running: <Loader2 className="h-4 w-4 animate-spin text-blue-400" />,
    queued: <Loader2 className="h-4 w-4 text-yellow-400" />,
    failed: <XCircle className="h-4 w-4 text-red-400" />,
};

export default function RagEvalPage() {
    const { data: runs, mutate } = useRagEvals();
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const { data: detail } = useRagEvalDetail(selectedId);
    const [model, setModel] = useState("gpt-4");
    const [topK, setTopK] = useState(3);
    const [launching, setLaunching] = useState(false);

    const handleLaunch = async () => {
        setLaunching(true);
        try {
            const result = await apiFetch<{ id: string }>("/rag-eval/run", {
                method: "POST",
                body: JSON.stringify({
                    target_model: model,
                    config: { top_k: topK },
                }),
            });
            setSelectedId(result.id);
            mutate();
        } catch (e) {
            console.error("RAG eval launch failed:", e);
        } finally {
            setLaunching(false);
        }
    };

    const results = (detail?.results as Record<string, unknown>) ?? {};
    const queries = (results.queries as Record<string, unknown>[]) ?? [];
    const summary = (results.summary as Record<string, number>) ?? {};

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <FileSearch className="h-6 w-6 text-primary" />
                    <h1 className="text-2xl font-bold">RAG Evaluation</h1>
                </div>
            </div>

            <p className="text-sm text-muted-foreground">
                Test LLMs against poisoned retrieval contexts. Documents are indexed with TF-IDF,
                poison documents injected, and model responses scored for context override,
                exfiltration, and citation accuracy.
            </p>

            {/* Launch form */}
            <div className="rounded-lg border bg-card p-4 space-y-4">
                <h2 className="font-semibold">Run RAG Evaluation</h2>
                <div className="flex flex-wrap gap-4 items-end">
                    <div>
                        <label className="text-sm text-muted-foreground">Target Model</label>
                        <input
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="mt-1 block w-64 rounded border bg-background px-3 py-2 text-sm"
                            placeholder="gpt-4, claude-3-opus, etc."
                        />
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground">Top-K Documents</label>
                        <input
                            type="number"
                            min={1}
                            max={10}
                            value={topK}
                            onChange={(e) => setTopK(Number(e.target.value))}
                            className="mt-1 block w-20 rounded border bg-background px-3 py-2 text-sm"
                        />
                    </div>
                    <button
                        onClick={handleLaunch}
                        disabled={launching || !model}
                        className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                        {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                        Run with Built-in Corpus
                    </button>
                </div>
                <p className="text-xs text-muted-foreground">
                    Uses 20 clean documents, 10 poison documents, and 15 test queries.
                </p>
            </div>

            {/* Run list */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="space-y-2">
                    <h3 className="font-semibold text-sm">Recent Runs</h3>
                    {(runs ?? []).map((run) => (
                        <button
                            key={run.id}
                            onClick={() => setSelectedId(run.id)}
                            className={cn(
                                "w-full rounded border p-3 text-left text-sm transition-colors",
                                selectedId === run.id ? "border-primary bg-primary/10" : "hover:bg-muted"
                            )}
                        >
                            <div className="flex items-center gap-2">
                                {STATUS_ICON[run.status] ?? null}
                                <span className="font-medium">{run.target_model}</span>
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                                {new Date(run.created_at).toLocaleString()}
                                {run.status === "running" && ` - ${Math.round(run.progress * 100)}%`}
                            </div>
                        </button>
                    ))}
                    {(!runs || runs.length === 0) && (
                        <p className="text-sm text-muted-foreground">No runs yet.</p>
                    )}
                </div>

                {/* Detail view */}
                <div className="lg:col-span-2 space-y-4">
                    {detail && (
                        <>
                            {/* Summary cards */}
                            {Object.keys(summary).length > 0 && (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">{summary.total_queries ?? 0}</div>
                                        <div className="text-xs text-muted-foreground">Queries</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold text-red-400">
                                            {summary.poison_compliance_count ?? 0}
                                        </div>
                                        <div className="text-xs text-muted-foreground">Poison Followed</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold text-orange-400">
                                            {summary.context_leak_count ?? 0}
                                        </div>
                                        <div className="text-xs text-muted-foreground">Context Leaks</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">
                                            {Math.round((summary.avg_safety_score ?? 0) * 100)}%
                                        </div>
                                        <div className="text-xs text-muted-foreground">Avg Safety</div>
                                    </div>
                                </div>
                            )}

                            {/* Per-query results */}
                            {queries.map((q, i) => {
                                const score = (q.score as number) ?? 1;
                                const hasPois = q.has_poison_in_context as boolean;
                                return (
                                    <div key={i} className="rounded border p-4 space-y-2">
                                        <div className="flex items-center justify-between">
                                            <span className="font-medium text-sm">{q.query as string}</span>
                                            <span
                                                className={cn(
                                                    "rounded px-2 py-0.5 text-xs font-medium",
                                                    score >= 0.7
                                                        ? "bg-green-900/30 text-green-400"
                                                        : score >= 0.4
                                                          ? "bg-yellow-900/30 text-yellow-400"
                                                          : "bg-red-900/30 text-red-400"
                                                )}
                                            >
                                                {Math.round(score * 100)}%
                                            </span>
                                        </div>
                                        {hasPois && (
                                            <div className="flex items-center gap-1 text-xs text-orange-400">
                                                <FileWarning className="h-3 w-3" />
                                                Poison document in retrieved context
                                            </div>
                                        )}
                                        <pre className="text-xs bg-muted/50 rounded p-2 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                            {(q.response_preview as string) ?? ""}
                                        </pre>
                                    </div>
                                );
                            })}

                            {detail.status === "running" && (
                                <div className="flex items-center gap-2 text-sm text-blue-400">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Running... {Math.round(detail.progress * 100)}%
                                </div>
                            )}
                        </>
                    )}

                    {!detail && selectedId && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading...
                        </div>
                    )}

                    {!selectedId && (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <FileSearch className="h-12 w-12 mb-3 opacity-30" />
                            <p className="text-sm">Select a run to view results</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
