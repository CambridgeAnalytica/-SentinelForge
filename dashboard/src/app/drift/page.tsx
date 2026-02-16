"use client";

import { useState } from "react";
import { useDriftBaselines, useDriftHistory } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    BarChart,
    Bar,
    Cell,
} from "recharts";
import { TrendingDown, AlertTriangle } from "lucide-react";

const CATEGORY_COLORS = [
    "#22c55e",
    "#0ea5e9",
    "#8b5cf6",
    "#f97316",
    "#eab308",
    "#ec4899",
    "#14b8a6",
    "#ef4444",
];

export default function DriftPage() {
    const { data: baselines, isLoading } = useDriftBaselines();
    const [selectedBaseline, setSelectedBaseline] = useState<string | null>(null);
    const { data: history } = useDriftHistory(selectedBaseline);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    const allBaselines = baselines ?? [];
    const currentBaseline = allBaselines.find((b) => b.id === selectedBaseline);

    // Build timeline data from history
    const timelineData = (history ?? []).map((h, i) => ({
        point: `T${i + 1}`,
        drift: Math.round(h.overall_drift * 100),
        ...Object.fromEntries(
            Object.entries(h.current_scores).map(([k, v]) => [k, Math.round(v * 100)])
        ),
    }));

    // Category breakdown from latest comparison
    const latestComparison = history?.[history.length - 1];
    const categoryData = latestComparison
        ? Object.entries(latestComparison.current_scores).map(([name, score]) => ({
            name,
            score: Math.round(score * 100),
            delta: Math.round((latestComparison.deltas[name] ?? 0) * 100),
        }))
        : currentBaseline
            ? Object.entries(currentBaseline.scores).map(([name, score]) => ({
                name,
                score: Math.round(score * 100),
                delta: 0,
            }))
            : [];

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Drift Timeline</h2>
                    <p className="text-sm text-muted-foreground">
                        Track safety score degradation over time
                    </p>
                </div>

                {/* Baseline selector */}
                <select
                    value={selectedBaseline ?? ""}
                    onChange={(e) => setSelectedBaseline(e.target.value || null)}
                    className="h-9 rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    <option value="">Select baseline...</option>
                    {allBaselines.map((b) => (
                        <option key={b.id} value={b.id}>
                            {b.model} — {b.test_suite}
                        </option>
                    ))}
                </select>
            </div>

            {!selectedBaseline ? (
                <div className="flex h-64 items-center justify-center rounded-xl border border-border bg-card text-sm text-muted-foreground">
                    <TrendingDown className="mr-2 h-5 w-5" />
                    Select a baseline to view drift data
                </div>
            ) : (
                <>
                    {/* Overall drift indicator */}
                    {latestComparison && (
                        <div className="flex items-center gap-4 rounded-xl border border-border bg-card p-4">
                            <div
                                className={cn(
                                    "flex h-12 w-12 items-center justify-center rounded-full text-lg font-bold",
                                    latestComparison.overall_drift > 0.1
                                        ? "bg-critical/15 text-critical"
                                        : latestComparison.overall_drift > 0.05
                                            ? "bg-medium/15 text-medium"
                                            : "bg-low/15 text-low"
                                )}
                            >
                                {Math.round(latestComparison.overall_drift * 100)}%
                            </div>
                            <div>
                                <p className="font-semibold text-foreground">Overall Drift</p>
                                <p className="text-xs text-muted-foreground">
                                    {latestComparison.degraded_categories.length} degraded{" "}
                                    {latestComparison.degraded_categories.length === 1
                                        ? "category"
                                        : "categories"}
                                </p>
                            </div>
                            {latestComparison.degraded_categories.length > 0 && (
                                <div className="ml-auto flex items-center gap-1 text-xs text-warning">
                                    <AlertTriangle className="h-3.5 w-3.5" />
                                    {latestComparison.degraded_categories.join(", ")}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Timeline chart */}
                    <div className="rounded-xl border border-border bg-card p-4">
                        <h3 className="mb-3 text-sm font-semibold text-foreground">
                            Safety Score Timeline
                        </h3>
                        <div className="h-64">
                            {timelineData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={timelineData}>
                                        <XAxis
                                            dataKey="point"
                                            tick={{ fontSize: 10, fill: "#94a3b8" }}
                                            axisLine={false}
                                            tickLine={false}
                                        />
                                        <YAxis
                                            domain={[0, 100]}
                                            tick={{ fontSize: 10, fill: "#94a3b8" }}
                                            axisLine={false}
                                            tickLine={false}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                background: "hsl(224 71% 4%)",
                                                border: "1px solid hsl(215 27% 16%)",
                                                borderRadius: "0.5rem",
                                                color: "#fff",
                                            }}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="drift"
                                            stroke="#ef4444"
                                            strokeWidth={2}
                                            dot={{ fill: "#ef4444", r: 3 }}
                                            name="Drift %"
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                                    Run drift comparisons to see timeline data
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Category breakdown */}
                    {categoryData.length > 0 && (
                        <div className="rounded-xl border border-border bg-card p-4">
                            <h3 className="mb-3 text-sm font-semibold text-foreground">
                                Category Scores
                            </h3>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={categoryData} layout="vertical">
                                        <XAxis
                                            type="number"
                                            domain={[0, 100]}
                                            tick={{ fontSize: 10, fill: "#94a3b8" }}
                                            axisLine={false}
                                            tickLine={false}
                                        />
                                        <YAxis
                                            type="category"
                                            dataKey="name"
                                            tick={{ fontSize: 10, fill: "#94a3b8" }}
                                            axisLine={false}
                                            tickLine={false}
                                            width={120}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                background: "hsl(224 71% 4%)",
                                                border: "1px solid hsl(215 27% 16%)",
                                                borderRadius: "0.5rem",
                                                color: "#fff",
                                            }}
                                        />
                                        <Bar dataKey="score" radius={[0, 4, 4, 0]} barSize={18}>
                                            {categoryData.map((_, i) => (
                                                <Cell
                                                    key={i}
                                                    fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]}
                                                />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
