"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useMultimodalEvals, useMultimodalEvalDetail } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import {
    ImageIcon,
    Play,
    Loader2,
    CheckCircle2,
    XCircle,
    Eye,
} from "lucide-react";

const STATUS_ICON: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-4 w-4 text-green-400" />,
    running: <Loader2 className="h-4 w-4 animate-spin text-blue-400" />,
    queued: <Loader2 className="h-4 w-4 text-yellow-400" />,
    failed: <XCircle className="h-4 w-4 text-red-400" />,
};

export default function MultimodalEvalPage() {
    const { data: runs, mutate } = useMultimodalEvals();
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const { data: detail } = useMultimodalEvalDetail(selectedId);
    const [model, setModel] = useState("gpt-4o");
    const [launching, setLaunching] = useState(false);

    const handleLaunch = async () => {
        setLaunching(true);
        try {
            const result = await apiFetch<{ id: string }>("/multimodal-eval/run", {
                method: "POST",
                body: JSON.stringify({
                    target_model: model,
                    config: {},
                }),
            });
            setSelectedId(result.id);
            mutate();
        } catch (e) {
            console.error("Multimodal eval launch failed:", e);
        } finally {
            setLaunching(false);
        }
    };

    const results = (detail?.results as Record<string, unknown>) ?? {};
    const images = (results.images as Record<string, unknown>[]) ?? [];
    const summary = (results.summary as Record<string, number>) ?? {};

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <ImageIcon className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">Multimodal Evaluation</h1>
            </div>

            <p className="text-sm text-muted-foreground">
                Generate adversarial images (text overlay, OCR injection, metadata injection)
                and send them to vision-capable LLMs. Tests whether models follow embedded
                text instructions.
            </p>

            {/* Launch form */}
            <div className="rounded-lg border bg-card p-4 space-y-4">
                <h2 className="font-semibold">Run Multimodal Evaluation</h2>
                <div className="flex flex-wrap gap-4 items-end">
                    <div>
                        <label className="text-sm text-muted-foreground">Target Model (Vision-capable)</label>
                        <input
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="mt-1 block w-64 rounded border bg-background px-3 py-2 text-sm"
                            placeholder="gpt-4o, claude-3-opus, etc."
                        />
                    </div>
                    <button
                        onClick={handleLaunch}
                        disabled={launching || !model}
                        className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                        {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                        Run with 8 Built-in Templates
                    </button>
                </div>
                <p className="text-xs text-muted-foreground">
                    8 adversarial image templates x 4 queries = 32 tests.
                    Requires a vision-capable model (GPT-4o, Claude 3, etc.)
                </p>
            </div>

            {/* Run list + detail */}
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
                            </div>
                        </button>
                    ))}
                    {(!runs || runs.length === 0) && (
                        <p className="text-sm text-muted-foreground">No runs yet.</p>
                    )}
                </div>

                <div className="lg:col-span-2 space-y-4">
                    {detail && (
                        <>
                            {Object.keys(summary).length > 0 && (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">{summary.total_tests ?? 0}</div>
                                        <div className="text-xs text-muted-foreground">Tests</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold text-red-400">
                                            {summary.injection_successes ?? 0}
                                        </div>
                                        <div className="text-xs text-muted-foreground">Injections Succeeded</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">
                                            {summary.images_generated ?? 0}
                                        </div>
                                        <div className="text-xs text-muted-foreground">Images</div>
                                    </div>
                                    <div className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">
                                            {Math.round((summary.avg_safety_score ?? 0) * 100)}%
                                        </div>
                                        <div className="text-xs text-muted-foreground">Avg Safety</div>
                                    </div>
                                </div>
                            )}

                            {images.map((img, i) => {
                                const score = (img.score as number) ?? 1;
                                return (
                                    <div key={i} className="rounded border p-4 space-y-2">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className={cn(
                                                        "rounded px-2 py-0.5 text-xs font-medium",
                                                        (img.image_type as string) === "text_overlay"
                                                            ? "bg-blue-900/30 text-blue-400"
                                                            : (img.image_type as string) === "ocr_injection"
                                                              ? "bg-purple-900/30 text-purple-400"
                                                              : "bg-gray-900/30 text-gray-400"
                                                    )}
                                                >
                                                    {img.image_type as string}
                                                </span>
                                                <span className="text-sm text-muted-foreground truncate max-w-sm">
                                                    {img.query as string}
                                                </span>
                                            </div>
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
                                        <div className="text-xs text-muted-foreground">
                                            Embedded: &quot;{(img.embedded_text as string)?.slice(0, 100)}&quot;
                                        </div>
                                        <pre className="text-xs bg-muted/50 rounded p-2 whitespace-pre-wrap max-h-24 overflow-y-auto">
                                            {(img.response_preview as string) ?? ""}
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

                    {!selectedId && (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <ImageIcon className="h-12 w-12 mb-3 opacity-30" />
                            <p className="text-sm">Select a run to view results</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
