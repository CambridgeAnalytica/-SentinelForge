"use client";

import { useState } from "react";
import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import { cn, capitalize } from "@/lib/utils";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";
import {
    TrendingUp,
    TrendingDown,
    Minus,
    AlertTriangle,
} from "lucide-react";

interface TrendData {
    model: string | null;
    days: number;
    available_models: string[];
    data_points: {
        date: string;
        run_id: string;
        scenario_id: string;
        target_model: string;
        pass_rate: number | null;
        findings_count: number;
        critical_count: number;
    }[];
    summary: {
        avg_pass_rate: number | null;
        trend: string;
        worst_scenario: string | null;
        total_runs: number;
    };
}

const SCENARIO_COLORS = [
    "#22c55e", "#3b82f6", "#ef4444", "#f59e0b", "#a855f7",
    "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    "#e879f9", "#fb923c", "#2dd4bf", "#facc15", "#818cf8", "#f43f5e",
];

const RANGE_OPTIONS = [
    { label: "7d", value: 7 },
    { label: "30d", value: 30 },
    { label: "90d", value: 90 },
];

export default function TrendsPage() {
    const [selectedModel, setSelectedModel] = useState<string>("");
    const [days, setDays] = useState(30);

    const { data: trends, isLoading } = useSWR<TrendData>(
        `/attacks/trends?days=${days}${selectedModel ? `&model=${encodeURIComponent(selectedModel)}` : ""}`,
        (p: string) => apiFetch<TrendData>(p),
        { refreshInterval: 30000 }
    );

    const summary = trends?.summary;
    const dataPoints = trends?.data_points ?? [];
    const models = trends?.available_models ?? [];

    // Build chart data: group by date, one key per scenario
    const scenarios = [...new Set(dataPoints.map((d) => d.scenario_id))];
    const byDate: Record<string, Record<string, number>> = {};
    for (const dp of dataPoints) {
        if (dp.date && dp.pass_rate != null) {
            if (!byDate[dp.date]) byDate[dp.date] = {};
            byDate[dp.date][dp.scenario_id] = dp.pass_rate;
        }
    }
    const chartData = Object.entries(byDate)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, vals]) => ({ date, ...vals }));

    const TrendIcon = summary?.trend === "improving" ? TrendingUp
        : summary?.trend === "degrading" ? TrendingDown : Minus;
    const trendColor = summary?.trend === "improving" ? "text-low"
        : summary?.trend === "degrading" ? "text-critical" : "text-muted-foreground";

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Safety Trends</h2>
                    <p className="text-sm text-muted-foreground">
                        Historical pass rates per model and scenario over time
                    </p>
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-3">
                <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                    <option value="">All models</option>
                    {models.map((m) => (
                        <option key={m} value={m}>{m}</option>
                    ))}
                </select>
                <div className="flex rounded-md border border-border">
                    {RANGE_OPTIONS.map((opt) => (
                        <button
                            key={opt.value}
                            onClick={() => setDays(opt.value)}
                            className={cn(
                                "px-3 py-1.5 text-xs font-medium transition-colors",
                                days === opt.value
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            {opt.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Summary cards */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs font-medium text-muted-foreground">Avg Pass Rate</p>
                    <p className={cn("mt-1 text-2xl font-bold", summary?.avg_pass_rate != null && summary.avg_pass_rate >= 0.8 ? "text-low" : summary?.avg_pass_rate != null && summary.avg_pass_rate >= 0.5 ? "text-medium" : "text-critical")}>
                        {summary?.avg_pass_rate != null ? `${Math.round(summary.avg_pass_rate * 100)}%` : "—"}
                    </p>
                </div>
                <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs font-medium text-muted-foreground">Trend</p>
                    <div className="mt-1 flex items-center gap-2">
                        <TrendIcon className={cn("h-5 w-5", trendColor)} />
                        <span className={cn("text-lg font-bold", trendColor)}>
                            {capitalize(summary?.trend ?? "—")}
                        </span>
                    </div>
                </div>
                <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs font-medium text-muted-foreground">Worst Scenario</p>
                    <p className="mt-1 text-lg font-bold text-foreground flex items-center gap-2">
                        {summary?.worst_scenario ? (
                            <>
                                <AlertTriangle className="h-4 w-4 text-critical" />
                                {summary.worst_scenario}
                            </>
                        ) : "—"}
                    </p>
                </div>
                <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs font-medium text-muted-foreground">Total Runs</p>
                    <p className="mt-1 text-2xl font-bold text-foreground">{summary?.total_runs ?? 0}</p>
                </div>
            </div>

            {/* Line chart */}
            <div className="rounded-xl border border-border bg-card p-4">
                <h3 className="mb-3 text-sm font-semibold text-foreground">
                    Pass Rate Over Time
                </h3>
                <div className="h-72">
                    {isLoading ? (
                        <div className="flex h-full items-center justify-center text-muted-foreground">Loading...</div>
                    ) : chartData.length === 0 ? (
                        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                            No trend data yet. Run scans to see trends here.
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData}>
                                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                                <YAxis
                                    domain={[0, 1]}
                                    tickFormatter={(v) => `${Math.round(v * 100)}%`}
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
                                    formatter={(value: number) => `${Math.round(value * 100)}%`}
                                />
                                <Legend wrapperStyle={{ fontSize: 11 }} />
                                {scenarios.map((s, i) => (
                                    <Line
                                        key={s}
                                        type="monotone"
                                        dataKey={s}
                                        stroke={SCENARIO_COLORS[i % SCENARIO_COLORS.length]}
                                        strokeWidth={2}
                                        dot={{ r: 3 }}
                                        connectNulls
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </div>
        </div>
    );
}
