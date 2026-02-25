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
    ChevronDown,
    ChevronRight,
    Shield,
    ShieldAlert,
    ShieldCheck,
    BookOpen,
    Bug,
    Eye,
} from "lucide-react";

const STATUS_ICON: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-4 w-4 text-green-400" />,
    running: <Loader2 className="h-4 w-4 animate-spin text-blue-400" />,
    queued: <Loader2 className="h-4 w-4 text-yellow-400" />,
    failed: <XCircle className="h-4 w-4 text-red-400" />,
};

function ScoreBadge({ score }: { score: number }) {
    const pct = Math.round(score * 100);
    return (
        <span
            className={cn(
                "rounded px-2 py-0.5 text-xs font-bold tabular-nums",
                score >= 0.7
                    ? "bg-green-900/30 text-green-400"
                    : score >= 0.4
                      ? "bg-yellow-900/30 text-yellow-400"
                      : "bg-red-900/30 text-red-400"
            )}
        >
            {pct}%
        </span>
    );
}

function IndicatorPills({ indicators }: { indicators: Record<string, string[]> }) {
    const entries = Object.entries(indicators).filter(([, v]) => v.length > 0);
    if (entries.length === 0) return null;

    const colorMap: Record<string, string> = {
        safe_behaviors: "bg-green-900/30 text-green-400",
        override_compliance: "bg-red-900/30 text-red-400",
        context_exfiltration: "bg-orange-900/30 text-orange-400",
        citation_fabrication: "bg-red-900/30 text-red-300",
    };

    const labelMap: Record<string, string> = {
        safe_behaviors: "Safe",
        override_compliance: "Override",
        context_exfiltration: "Exfil",
        citation_fabrication: "Fabrication",
    };

    return (
        <div className="flex flex-wrap gap-1 mt-1">
            {entries.map(([cat, items]) =>
                items.map((item, j) => (
                    <span
                        key={`${cat}-${j}`}
                        className={cn(
                            "rounded px-1.5 py-0.5 text-[10px] font-mono",
                            colorMap[cat] ?? "bg-muted text-muted-foreground"
                        )}
                        title={`${labelMap[cat] ?? cat}: ${item}`}
                    >
                        {labelMap[cat]}: &ldquo;{item.slice(0, 30)}
                        {item.length > 30 ? "..." : ""}&rdquo;
                    </span>
                ))
            )}
        </div>
    );
}

interface QueryResult {
    query: string;
    category: string;
    retrieved_docs: {
        title: string;
        is_poison: boolean;
        similarity: number;
        content_preview: string;
        injection_type: string | null;
    }[];
    has_poison_in_context: boolean;
    rag_prompt: string;
    response: string;
    response_preview: string;
    score: number;
    score_reason: string;
    score_indicators: Record<string, string[]>;
}

function QueryResultCard({ q, index }: { q: QueryResult; index: number }) {
    const [expanded, setExpanded] = useState(false);
    const [showPrompt, setShowPrompt] = useState(false);

    const score = q.score ?? 1;
    const hasPois = q.has_poison_in_context;
    const docs = q.retrieved_docs ?? [];

    return (
        <div className="rounded-lg border border-border bg-card overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-muted/30 transition-colors"
            >
                {expanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
                <span className="text-xs text-muted-foreground w-6">#{index + 1}</span>
                <span className="font-medium text-sm flex-1 text-left">{q.query}</span>
                <div className="flex items-center gap-2 shrink-0">
                    {q.category && q.category !== "unknown" && (
                        <span className="rounded px-1.5 py-0.5 text-[10px] bg-muted text-muted-foreground">
                            {q.category}
                        </span>
                    )}
                    {hasPois && (
                        <span title="Poison in context"><FileWarning className="h-4 w-4 text-orange-400" /></span>
                    )}
                    <ScoreBadge score={score} />
                </div>
            </button>

            {/* Collapsed summary */}
            {!expanded && (
                <div className="px-4 pb-3 pl-16">
                    <p className="text-xs text-muted-foreground italic">{q.score_reason}</p>
                </div>
            )}

            {/* Expanded detail */}
            {expanded && (
                <div className="border-t border-border px-4 py-3 space-y-4">
                    {/* Score explanation */}
                    <div className="flex items-start gap-2">
                        {score >= 0.7 ? (
                            <ShieldCheck className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                        ) : score >= 0.4 ? (
                            <Shield className="h-4 w-4 text-yellow-400 mt-0.5 shrink-0" />
                        ) : (
                            <ShieldAlert className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
                        )}
                        <div>
                            <p className="text-sm font-medium">
                                Score: {Math.round(score * 100)}% &mdash; {q.score_reason}
                            </p>
                            {q.score_indicators && (
                                <IndicatorPills indicators={q.score_indicators} />
                            )}
                        </div>
                    </div>

                    {/* Retrieved Documents */}
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <BookOpen className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Retrieved Documents ({docs.length})
                            </span>
                        </div>
                        <div className="space-y-2">
                            {docs.map((doc, di) => (
                                <div
                                    key={di}
                                    className={cn(
                                        "rounded border p-2.5 text-xs",
                                        doc.is_poison
                                            ? "border-red-800/50 bg-red-950/20"
                                            : "border-border bg-muted/20"
                                    )}
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium">{doc.title}</span>
                                            {doc.is_poison && (
                                                <span className="rounded px-1.5 py-0.5 text-[10px] font-bold bg-red-900/40 text-red-400 flex items-center gap-1">
                                                    <Bug className="h-3 w-3" /> POISON
                                                </span>
                                            )}
                                            {doc.injection_type && (
                                                <span className="rounded px-1.5 py-0.5 text-[10px] bg-orange-900/30 text-orange-400">
                                                    {doc.injection_type}
                                                </span>
                                            )}
                                        </div>
                                        <span className="text-muted-foreground tabular-nums">
                                            sim: {(doc.similarity * 100).toFixed(1)}%
                                        </span>
                                    </div>
                                    <p className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
                                        {doc.content_preview}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* RAG Prompt toggle */}
                    {q.rag_prompt && (
                        <div>
                            <button
                                onClick={() => setShowPrompt(!showPrompt)}
                                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <Eye className="h-3 w-3" />
                                {showPrompt ? "Hide" : "Show"} full RAG prompt sent to model
                            </button>
                            {showPrompt && (
                                <pre className="mt-2 text-xs bg-muted/30 rounded p-3 whitespace-pre-wrap max-h-64 overflow-y-auto border border-border font-mono leading-relaxed">
                                    {q.rag_prompt}
                                </pre>
                            )}
                        </div>
                    )}

                    {/* Model Response */}
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Model Response
                            </span>
                        </div>
                        <pre className="text-xs bg-muted/30 rounded p-3 whitespace-pre-wrap max-h-64 overflow-y-auto border border-border leading-relaxed">
                            {q.response ?? q.response_preview ?? ""}
                        </pre>
                    </div>
                </div>
            )}
        </div>
    );
}

export default function RagEvalPage() {
    const { data: runs, mutate } = useRagEvals();
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const { data: detail } = useRagEvalDetail(selectedId);
    const [provider, setProvider] = useState("ollama");
    const [model, setModel] = useState("llama3.2:3b");
    const [endpoint, setEndpoint] = useState("");
    const [topK, setTopK] = useState(3);
    const [launching, setLaunching] = useState(false);

    const PROVIDER_MODELS: Record<string, string> = {
        ollama: "llama3.2:3b",
        openai: "gpt-4o",
        anthropic: "claude-sonnet-4-5-20250929",
        azure_openai: "gpt-4o",
        azure_ai: "Phi-4",
        bedrock: "anthropic.claude-3-5-sonnet-20241022-v2:0",
        custom: "custom-model",
    };

    const handleLaunch = async () => {
        setLaunching(true);
        try {
            const cfg: Record<string, unknown> = { top_k: topK, provider };
            if (endpoint.trim()) cfg.base_url = endpoint.trim();
            const result = await apiFetch<{ id: string }>("/rag-eval/run", {
                method: "POST",
                body: JSON.stringify({
                    target_model: model,
                    config: cfg,
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
    const queries = (results.queries as QueryResult[]) ?? [];
    const summary = (results.summary as Record<string, number>) ?? {};

    // Compute category breakdown
    const categoryBreakdown: Record<string, { count: number; avgScore: number }> = {};
    for (const q of queries) {
        const cat = q.category || "unknown";
        if (!categoryBreakdown[cat]) categoryBreakdown[cat] = { count: 0, avgScore: 0 };
        categoryBreakdown[cat].count += 1;
        categoryBreakdown[cat].avgScore += q.score;
    }
    for (const cat of Object.keys(categoryBreakdown)) {
        categoryBreakdown[cat].avgScore /= categoryBreakdown[cat].count;
    }

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
                        <label className="text-sm text-muted-foreground">Provider</label>
                        <select
                            value={provider}
                            onChange={(e) => {
                                setProvider(e.target.value);
                                setModel(PROVIDER_MODELS[e.target.value] ?? "");
                            }}
                            className="mt-1 block w-40 rounded border bg-background px-3 py-2 text-sm"
                        >
                            <option value="ollama">Ollama (Local)</option>
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="azure_openai">Azure OpenAI</option>
                            <option value="azure_ai">Azure AI</option>
                            <option value="bedrock">AWS Bedrock</option>
                            <option value="custom">Custom Gateway</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground">Target Model</label>
                        <input
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="mt-1 block w-56 rounded border bg-background px-3 py-2 text-sm"
                            placeholder={PROVIDER_MODELS[provider] ?? "model-name"}
                        />
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground">Top-K</label>
                        <input
                            type="number"
                            min={1}
                            max={10}
                            value={topK}
                            onChange={(e) => setTopK(Number(e.target.value))}
                            className="mt-1 block w-16 rounded border bg-background px-3 py-2 text-sm"
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
                <div>
                    <label className="text-sm text-muted-foreground">Endpoint Override (optional)</label>
                    <input
                        value={endpoint}
                        onChange={(e) => setEndpoint(e.target.value)}
                        className="mt-1 block w-full rounded border bg-background px-3 py-2 text-sm"
                        placeholder="Leave blank for default. e.g. http://localhost:11434/v1"
                    />
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
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">{summary.total_queries ?? 0}</div>
                                        <div className="text-xs text-muted-foreground">Queries</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">{summary.documents_indexed ?? 0}</div>
                                        <div className="text-xs text-muted-foreground">Docs Indexed</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold text-orange-400">{summary.poison_documents ?? 0}</div>
                                        <div className="text-xs text-muted-foreground">Poison Docs</div>
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

                            {/* Category breakdown */}
                            {Object.keys(categoryBreakdown).length > 1 && (
                                <div className="rounded border p-3">
                                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                                        Score by Category
                                    </h4>
                                    <div className="flex flex-wrap gap-2">
                                        {Object.entries(categoryBreakdown).map(([cat, data]) => (
                                            <div key={cat} className="flex items-center gap-2 rounded bg-muted/30 px-2 py-1">
                                                <span className="text-xs">{cat}</span>
                                                <ScoreBadge score={data.avgScore} />
                                                <span className="text-[10px] text-muted-foreground">({data.count})</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Per-query results */}
                            <div className="space-y-2">
                                {queries.map((q, i) => (
                                    <QueryResultCard key={i} q={q} index={i} />
                                ))}
                            </div>

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
