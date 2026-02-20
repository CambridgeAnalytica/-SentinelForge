"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useCalibrations, useCalibrationDetail } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import {
    Target,
    Play,
    Loader2,
    CheckCircle2,
    XCircle,
    Zap,
} from "lucide-react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
} from "recharts";

const STATUS_ICON: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-4 w-4 text-green-400" />,
    running: <Loader2 className="h-4 w-4 animate-spin text-blue-400" />,
    queued: <Loader2 className="h-4 w-4 text-yellow-400" />,
    failed: <XCircle className="h-4 w-4 text-red-400" />,
};

export default function CalibrationPage() {
    const { data: runs, mutate } = useCalibrations();
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const { data: detail } = useCalibrationDetail(selectedId);
    const [model, setModel] = useState("gpt-4");
    const [launching, setLaunching] = useState(false);
    const [applying, setApplying] = useState(false);

    const handleLaunch = async () => {
        setLaunching(true);
        try {
            const result = await apiFetch<{ id: string }>("/scoring/calibrate", {
                method: "POST",
                body: JSON.stringify({ target_model: model, config: {} }),
            });
            setSelectedId(result.id);
            mutate();
        } catch (e) {
            console.error("Calibration launch failed:", e);
        } finally {
            setLaunching(false);
        }
    };

    const handleApply = async () => {
        if (!selectedId) return;
        setApplying(true);
        try {
            await apiFetch(`/scoring/calibrations/${selectedId}/apply`, {
                method: "POST",
            });
            alert("Threshold applied successfully!");
        } catch (e) {
            console.error("Apply failed:", e);
        } finally {
            setApplying(false);
        }
    };

    const metrics = detail?.metrics ?? {};
    const cm = detail?.confusion_matrix ?? {};
    const rocCurve = detail?.roc_curve ?? [];
    const recommended = detail?.recommended_threshold;

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Target className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">Scoring Calibration</h1>
            </div>

            <p className="text-sm text-muted-foreground">
                Run 50 known-safe and 50 known-unsafe prompts to validate and optimize
                the scoring engine threshold. Generates ROC curves and recommends optimal thresholds.
            </p>

            {/* Launch form */}
            <div className="rounded-lg border bg-card p-4 space-y-4">
                <h2 className="font-semibold">Run Calibration</h2>
                <div className="flex flex-wrap gap-4 items-end">
                    <div>
                        <label className="text-sm text-muted-foreground">Target Model</label>
                        <input
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            className="mt-1 block w-64 rounded border bg-background px-3 py-2 text-sm"
                        />
                    </div>
                    <button
                        onClick={handleLaunch}
                        disabled={launching || !model}
                        className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                        {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                        Calibrate (100 prompts)
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Run list */}
                <div className="space-y-2">
                    <h3 className="font-semibold text-sm">Calibration Runs</h3>
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
                        <p className="text-sm text-muted-foreground">No calibration runs yet.</p>
                    )}
                </div>

                {/* Detail */}
                <div className="lg:col-span-2 space-y-4">
                    {detail && detail.status === "completed" && (
                        <>
                            {/* Metric cards */}
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                {(["precision", "recall", "f1", "accuracy"] as const).map((key) => (
                                    <div key={key} className="rounded border p-3 text-center">
                                        <div className="text-2xl font-bold">
                                            {Math.round(((metrics as Record<string, number>)[key] ?? 0) * 100)}%
                                        </div>
                                        <div className="text-xs text-muted-foreground capitalize">{key}</div>
                                    </div>
                                ))}
                                {recommended != null && (
                                    <div className="rounded border border-primary/50 p-3 text-center">
                                        <div className="text-2xl font-bold text-primary">{recommended}</div>
                                        <div className="text-xs text-muted-foreground">Recommended</div>
                                    </div>
                                )}
                            </div>

                            {/* Confusion matrix */}
                            {Object.keys(cm).length > 0 && (
                                <div>
                                    <h3 className="text-sm font-semibold mb-2">Confusion Matrix</h3>
                                    <div className="grid grid-cols-2 gap-1 max-w-xs">
                                        <div className="rounded bg-green-900/30 p-3 text-center">
                                            <div className="text-lg font-bold text-green-400">{cm.tp ?? 0}</div>
                                            <div className="text-xs text-muted-foreground">True Pos</div>
                                        </div>
                                        <div className="rounded bg-red-900/30 p-3 text-center">
                                            <div className="text-lg font-bold text-red-400">{cm.fp ?? 0}</div>
                                            <div className="text-xs text-muted-foreground">False Pos</div>
                                        </div>
                                        <div className="rounded bg-red-900/30 p-3 text-center">
                                            <div className="text-lg font-bold text-red-400">{cm.fn ?? 0}</div>
                                            <div className="text-xs text-muted-foreground">False Neg</div>
                                        </div>
                                        <div className="rounded bg-green-900/30 p-3 text-center">
                                            <div className="text-lg font-bold text-green-400">{cm.tn ?? 0}</div>
                                            <div className="text-xs text-muted-foreground">True Neg</div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ROC curve */}
                            {rocCurve.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-semibold mb-2">ROC Curve</h3>
                                    <div className="h-64 w-full">
                                        <ResponsiveContainer>
                                            <LineChart data={rocCurve}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                <XAxis
                                                    dataKey="fpr"
                                                    label={{ value: "False Positive Rate", position: "bottom", fontSize: 12 }}
                                                    tickFormatter={(v: number) => v.toFixed(1)}
                                                />
                                                <YAxis
                                                    dataKey="tpr"
                                                    label={{ value: "True Positive Rate", angle: -90, position: "left", fontSize: 12 }}
                                                    tickFormatter={(v: number) => v.toFixed(1)}
                                                />
                                                <Tooltip
                                                    formatter={(value?: number) => `${((value ?? 0) * 100).toFixed(0)}%`}
                                                    labelFormatter={(fpr: number) => `FPR: ${(fpr * 100).toFixed(0)}%`}
                                                />
                                                <Line
                                                    type="monotone"
                                                    dataKey="tpr"
                                                    stroke="#3b82f6"
                                                    strokeWidth={2}
                                                    dot={false}
                                                />
                                                {/* Diagonal reference line */}
                                                <ReferenceLine
                                                    segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                                                    stroke="#555"
                                                    strokeDasharray="5 5"
                                                />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            )}

                            {/* Apply button */}
                            {recommended != null && (
                                <button
                                    onClick={handleApply}
                                    disabled={applying}
                                    className="flex items-center gap-2 rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                                >
                                    {applying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                                    Apply Threshold ({recommended}) as Default
                                </button>
                            )}
                        </>
                    )}

                    {detail && detail.status === "running" && (
                        <div className="flex items-center gap-2 text-sm text-blue-400">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Calibrating... {Math.round(detail.progress * 100)}%
                        </div>
                    )}

                    {!selectedId && (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <Target className="h-12 w-12 mb-3 opacity-30" />
                            <p className="text-sm">Select a calibration run to view results</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
