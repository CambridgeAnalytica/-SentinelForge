"use client";

import { useState } from "react";
import { useComplianceFrameworks } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ShieldCheck, Download, Loader2, AlertTriangle } from "lucide-react";

export default function CompliancePage() {
    const { data: frameworksRaw, isLoading } = useComplianceFrameworks();
    const [activeFramework, setActiveFramework] = useState(0);
    const [summaryData, setSummaryData] = useState<Record<
        string,
        { covered: boolean; finding_count: number }
    > | null>(null);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [coveragePct, setCoveragePct] = useState(0);
    const [downloadLoading, setDownloadLoading] = useState(false);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    // API may return either an array or {frameworks: [...]}
    const allFrameworks = Array.isArray(frameworksRaw)
        ? frameworksRaw
        : frameworksRaw && typeof frameworksRaw === "object" && "frameworks" in (frameworksRaw as Record<string, unknown>)
            ? ((frameworksRaw as Record<string, unknown>).frameworks as typeof frameworksRaw)
            : (frameworksRaw ?? []) as typeof frameworksRaw;
    const current = allFrameworks[activeFramework];

    async function loadSummary(frameworkId: string) {
        setSummaryLoading(true);
        try {
            const resp = await api.get<{
                coverage_percentage?: number;
                categories?: {
                    id: string;
                    total_findings: number;
                }[];
            }>(`/compliance/summary?framework=${frameworkId}`);

            // Build category_coverage map from categories array
            const catCoverage: Record<string, { covered: boolean; finding_count: number }> = {};
            let totalCats = 0;
            let coveredCats = 0;
            for (const cat of resp.categories ?? []) {
                const covered = cat.total_findings > 0;
                catCoverage[cat.id] = { covered, finding_count: cat.total_findings };
                totalCats++;
                if (covered) coveredCats++;
            }
            setSummaryData(catCoverage);
            setCoveragePct(
                resp.coverage_percentage ?? (totalCats > 0 ? (coveredCats / totalCats) * 100 : 0)
            );
        } catch {
            setSummaryData(null);
            setCoveragePct(0);
        } finally {
            setSummaryLoading(false);
        }
    }

    async function handleDownload() {
        setDownloadLoading(true);
        try {
            const token = localStorage.getItem("sf_token");
            const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
            const url = `${base}/compliance/report?framework=${current?.id}&format=pdf${token ? `&token=${token}` : ""}`;
            window.open(url, "_blank");
        } catch {
            // silently fail
        } finally {
            setDownloadLoading(false);
        }
    }

    function handleTabChange(idx: number) {
        setActiveFramework(idx);
        setSummaryData(null);
        if (allFrameworks[idx]) {
            loadSummary(allFrameworks[idx].id);
        }
    }

    // Initialize on first load
    if (allFrameworks.length > 0 && summaryData === null && !summaryLoading) {
        loadSummary(allFrameworks[0].id);
    }

    // Check if current framework is Arcanum
    const isArcanum = current?.id === "arcanum_pi";

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">
                        Compliance View
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Coverage heatmaps for security compliance frameworks
                    </p>
                </div>
                <button
                    onClick={handleDownload}
                    disabled={downloadLoading || !current}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                    {downloadLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <Download className="h-4 w-4" />
                    )}
                    Download PDF
                </button>
            </div>

            {/* Framework tabs */}
            {allFrameworks.length > 0 ? (
                <>
                    <div className="flex border-b border-border">
                        {allFrameworks.map((fw, idx) => (
                            <button
                                key={fw.id}
                                onClick={() => handleTabChange(idx)}
                                className={cn(
                                    "px-4 py-2 text-sm font-medium transition-colors border-b-2",
                                    idx === activeFramework
                                        ? "border-primary text-primary"
                                        : "border-transparent text-muted-foreground hover:text-foreground"
                                )}
                            >
                                {fw.name}
                            </button>
                        ))}
                    </div>

                    {/* Summary stats + coverage progress */}
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                        <StatCard
                            label="Coverage"
                            value={`${Math.round(coveragePct)}%`}
                            color={
                                coveragePct >= 80
                                    ? "text-low"
                                    : coveragePct >= 50
                                        ? "text-medium"
                                        : "text-critical"
                            }
                        />
                        <StatCard
                            label="Total Categories"
                            value={String(current?.categories?.length ?? 0)}
                            color="text-foreground"
                        />
                        <StatCard
                            label="Covered"
                            value={String(
                                summaryData
                                    ? Object.values(summaryData).filter((c) => c.covered).length
                                    : 0
                            )}
                            color="text-low"
                        />
                    </div>

                    {/* Coverage progress bar */}
                    <div className="rounded-xl border border-border bg-card p-4">
                        <div className="mb-2 flex items-center justify-between text-sm">
                            <span className="font-medium text-foreground">
                                Overall Coverage
                            </span>
                            <span className="font-mono text-foreground">
                                {Math.round(coveragePct)}%
                            </span>
                        </div>
                        <div className="h-3 overflow-hidden rounded-full bg-secondary">
                            <div
                                className="h-full rounded-full transition-all duration-700"
                                style={{
                                    width: `${Math.max(coveragePct, 1)}%`,
                                    background: `linear-gradient(90deg, ${coveragePct >= 80
                                            ? "#22c55e"
                                            : coveragePct >= 50
                                                ? "#eab308"
                                                : "#ef4444"
                                        } 0%, ${coveragePct >= 80
                                            ? "#16a34a"
                                            : coveragePct >= 50
                                                ? "#ca8a04"
                                                : "#dc2626"
                                        } 100%)`,
                                }}
                            />
                        </div>
                    </div>

                    {/* Category findings bar chart */}
                    {summaryData && Object.keys(summaryData).length > 0 && (
                        <div className="rounded-xl border border-border bg-card p-4">
                            <h3 className="mb-3 text-sm font-semibold text-foreground">
                                Findings per Category
                            </h3>
                            <div className="space-y-2">
                                {(current?.categories ?? [])
                                    .map((cat) => ({
                                        name: cat.name,
                                        id: cat.id,
                                        count: summaryData?.[cat.id]?.finding_count ?? 0,
                                        covered: summaryData?.[cat.id]?.covered ?? false,
                                    }))
                                    .sort((a, b) => b.count - a.count)
                                    .map((cat) => {
                                        const maxCount = Math.max(
                                            ...Object.values(summaryData).map(
                                                (c) => c.finding_count
                                            ),
                                            1
                                        );
                                        return (
                                            <div
                                                key={cat.id}
                                                className="flex items-center gap-3"
                                            >
                                                <span className="w-40 shrink-0 truncate text-xs text-muted-foreground">
                                                    {cat.name}
                                                </span>
                                                <div className="relative flex-1 h-5">
                                                    <div
                                                        className={cn(
                                                            "absolute inset-y-0 left-0 rounded transition-all duration-500",
                                                            cat.covered
                                                                ? "bg-low/30"
                                                                : "bg-muted/30"
                                                        )}
                                                        style={{
                                                            width: `${Math.max(
                                                                (cat.count / maxCount) * 100,
                                                                cat.count > 0 ? 4 : 0
                                                            )}%`,
                                                        }}
                                                    />
                                                </div>
                                                <span className="w-8 shrink-0 text-right text-xs font-mono text-foreground">
                                                    {cat.count}
                                                </span>
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>
                    )}

                    {/* Coverage heatmap — enhanced for Arcanum */}
                    <div className="rounded-xl border border-border bg-card p-4">
                        <h3 className="mb-4 text-sm font-semibold text-foreground">
                            Coverage Heatmap — {current?.name}
                        </h3>
                        {summaryLoading ? (
                            <div className="flex h-48 items-center justify-center">
                                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
                                {(current?.categories ?? []).map((cat) => {
                                    const coverage = summaryData?.[cat.id];
                                    const covered = coverage?.covered ?? false;
                                    const count = coverage?.finding_count ?? 0;
                                    const sevBaseline = (cat as Record<string, unknown>).severity_baseline as string | undefined;
                                    const subcats = (cat as Record<string, unknown>).subcategories as string[] | undefined;
                                    const testTypes = (cat as Record<string, unknown>).test_types as string[] | undefined;

                                    return (
                                        <div
                                            key={cat.id}
                                            className={cn(
                                                "rounded-lg border p-3 transition-colors",
                                                covered
                                                    ? "border-low/30 bg-low/5"
                                                    : "border-border bg-card hover:bg-secondary/50"
                                            )}
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-mono text-muted-foreground">
                                                    {cat.id}
                                                </span>
                                                <div className="flex items-center gap-1">
                                                    {isArcanum && sevBaseline && (
                                                        <SeverityBadge severity={sevBaseline} />
                                                    )}
                                                    {covered && (
                                                        <ShieldCheck className="h-3.5 w-3.5 text-low" />
                                                    )}
                                                </div>
                                            </div>
                                            <p className="mt-1 text-sm font-medium text-foreground line-clamp-2">
                                                {cat.name}
                                            </p>
                                            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                                                {cat.description}
                                            </p>
                                            {count > 0 && (
                                                <p className="mt-1 text-xs text-low">
                                                    {count} finding{count !== 1 ? "s" : ""}
                                                </p>
                                            )}
                                            {/* Arcanum-specific: subcategories and test types */}
                                            {isArcanum && subcats && subcats.length > 0 && (
                                                <div className="mt-2 flex flex-wrap gap-1">
                                                    {subcats.slice(0, 4).map((sc) => (
                                                        <span
                                                            key={sc}
                                                            className="rounded-full bg-secondary px-1.5 py-0.5 text-[9px] text-muted-foreground"
                                                        >
                                                            {sc}
                                                        </span>
                                                    ))}
                                                    {subcats.length > 4 && (
                                                        <span className="text-[9px] text-muted-foreground">
                                                            +{subcats.length - 4}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                            {isArcanum && testTypes && testTypes.length > 0 && (
                                                <div className="mt-1 flex items-center gap-1">
                                                    <AlertTriangle className="h-2.5 w-2.5 text-muted-foreground" />
                                                    <span className="text-[9px] text-muted-foreground">
                                                        {testTypes.length} test type{testTypes.length !== 1 ? "s" : ""}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </>
            ) : (
                <div className="flex h-64 items-center justify-center rounded-xl border border-border bg-card text-sm text-muted-foreground">
                    No compliance frameworks configured
                </div>
            )}
        </div>
    );
}

function SeverityBadge({ severity }: { severity: string }) {
    const colors: Record<string, string> = {
        critical: "bg-red-500/20 text-red-400",
        high: "bg-orange-500/20 text-orange-400",
        medium: "bg-yellow-500/20 text-yellow-400",
        low: "bg-green-500/20 text-green-400",
    };
    return (
        <span
            className={cn(
                "rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase",
                colors[severity] ?? "bg-zinc-500/20 text-zinc-400"
            )}
        >
            {severity}
        </span>
    );
}

function StatCard({
    label,
    value,
    color,
}: {
    label: string;
    value: string;
    color: string;
}) {
    return (
        <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <p className={cn("mt-1 text-2xl font-bold", color)}>{value}</p>
        </div>
    );
}
