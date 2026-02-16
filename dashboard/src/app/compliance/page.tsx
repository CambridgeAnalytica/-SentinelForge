"use client";

import { useState } from "react";
import { useComplianceFrameworks } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ShieldCheck, Download, Loader2 } from "lucide-react";

export default function CompliancePage() {
    const { data: frameworks, isLoading } = useComplianceFrameworks();
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

    const allFrameworks = frameworks ?? [];
    const current = allFrameworks[activeFramework];

    async function loadSummary(frameworkId: string) {
        setSummaryLoading(true);
        try {
            const resp = await api.post<{
                coverage_percentage: number;
                category_coverage: Record<
                    string,
                    { covered: boolean; finding_count: number }
                >;
            }>("/compliance/summary", { framework_id: frameworkId });
            setSummaryData(resp.category_coverage);
            setCoveragePct(resp.coverage_percentage);
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
            const blob = await api.post<Blob>("/compliance/report", {
                framework_id: current?.id,
                format: "pdf",
            });
            const url = URL.createObjectURL(blob as Blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `compliance_${current?.id ?? "report"}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
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

                    {/* Summary stats */}
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

                    {/* Coverage heatmap */}
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
                                                {covered && (
                                                    <ShieldCheck className="h-3.5 w-3.5 text-low" />
                                                )}
                                            </div>
                                            <p className="mt-1 text-sm font-medium text-foreground line-clamp-2">
                                                {cat.name}
                                            </p>
                                            <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                                                {cat.description}
                                            </p>
                                            {count > 0 && (
                                                <p className="mt-1 text-xs text-low">
                                                    {count} finding{count !== 1 ? "s" : ""}
                                                </p>
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
