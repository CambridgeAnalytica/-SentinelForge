"use client";

import { useState, useMemo } from "react";
import { useAttackRuns, type Finding } from "@/hooks/use-api";
import { cn, severityBadge, capitalize, timeAgo } from "@/lib/utils";
import { Search, X, ChevronRight } from "lucide-react";

const SEVERITIES = ["critical", "high", "medium", "low", "info"];

export default function FindingsPage() {
    const { data: runs, isLoading } = useAttackRuns();
    const [severityFilter, setSeverityFilter] = useState<string>("");
    const [toolFilter, setToolFilter] = useState<string>("");
    const [techniqueFilter, setTechniqueFilter] = useState<string>("");
    const [searchQuery, setSearchQuery] = useState<string>("");
    const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

    // Aggregate findings from all runs
    const allFindings = useMemo(() => {
        return (runs ?? []).flatMap((r) =>
            (r.findings ?? []).map((f) => ({
                ...f,
                run_id: r.id,
                scenario_id: r.scenario_id,
                target_model: r.target_model,
            }))
        );
    }, [runs]);

    // Unique filter options
    const tools = useMemo(
        () => [...new Set(allFindings.map((f) => f.tool_name).filter(Boolean))],
        [allFindings]
    );
    const techniques = useMemo(
        () =>
            [
                ...new Set(allFindings.map((f) => f.mitre_technique).filter(Boolean)),
            ] as string[],
        [allFindings]
    );

    // Filtered results
    const filtered = useMemo(() => {
        return allFindings.filter((f) => {
            if (severityFilter && f.severity?.toLowerCase() !== severityFilter)
                return false;
            if (toolFilter && f.tool_name !== toolFilter) return false;
            if (techniqueFilter && f.mitre_technique !== techniqueFilter) return false;
            if (
                searchQuery &&
                !f.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
                !(f.description ?? "").toLowerCase().includes(searchQuery.toLowerCase())
            )
                return false;
            return true;
        });
    }, [allFindings, severityFilter, toolFilter, techniqueFilter, searchQuery]);

    const activeFilters =
        [severityFilter, toolFilter, techniqueFilter, searchQuery].filter(Boolean)
            .length > 0;

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-12 animate-pulse rounded-xl bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-foreground">
                    Findings Explorer
                </h2>
                <p className="text-sm text-muted-foreground">
                    {allFindings.length} findings across {runs?.length ?? 0} scans
                </p>
            </div>

            {/* Filter bar */}
            <div className="flex flex-wrap items-center gap-3">
                {/* Search */}
                <div className="relative flex-1 min-w-48">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search findings..."
                        className="h-9 w-full rounded-md border border-input bg-secondary pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                </div>

                {/* Severity */}
                <select
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                    className="h-9 rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    <option value="">All Severities</option>
                    {SEVERITIES.map((s) => (
                        <option key={s} value={s}>
                            {capitalize(s)}
                        </option>
                    ))}
                </select>

                {/* Tool */}
                <select
                    value={toolFilter}
                    onChange={(e) => setToolFilter(e.target.value)}
                    className="h-9 rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    <option value="">All Tools</option>
                    {tools.map((t) => (
                        <option key={t} value={t}>
                            {t}
                        </option>
                    ))}
                </select>

                {/* MITRE Technique */}
                <select
                    value={techniqueFilter}
                    onChange={(e) => setTechniqueFilter(e.target.value)}
                    className="h-9 rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                    <option value="">All Techniques</option>
                    {techniques.map((t) => (
                        <option key={t} value={t}>
                            {t}
                        </option>
                    ))}
                </select>

                {activeFilters && (
                    <button
                        onClick={() => {
                            setSeverityFilter("");
                            setToolFilter("");
                            setTechniqueFilter("");
                            setSearchQuery("");
                        }}
                        className="flex h-9 items-center gap-1 rounded-md border border-input px-3 text-xs text-muted-foreground hover:bg-secondary transition-colors"
                    >
                        <X className="h-3 w-3" /> Clear
                    </button>
                )}
            </div>

            {/* Results count */}
            <p className="text-xs text-muted-foreground">
                Showing {filtered.length} of {allFindings.length} findings
            </p>

            {/* Findings table */}
            <div className="rounded-xl border border-border bg-card">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                <th className="px-4 py-2 font-medium">Severity</th>
                                <th className="px-4 py-2 font-medium">Title</th>
                                <th className="px-4 py-2 font-medium">Tool</th>
                                <th className="px-4 py-2 font-medium">MITRE</th>
                                <th className="px-4 py-2 font-medium">Created</th>
                                <th className="px-4 py-2 font-medium"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={6}
                                        className="px-4 py-12 text-center text-muted-foreground"
                                    >
                                        No findings match your filters.
                                    </td>
                                </tr>
                            ) : (
                                filtered.slice(0, 100).map((f) => (
                                    <tr
                                        key={f.id}
                                        className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors cursor-pointer"
                                        onClick={() => setSelectedFinding(f)}
                                    >
                                        <td className="px-4 py-2.5">
                                            <span
                                                className={cn(
                                                    "rounded-full px-2 py-0.5 text-xs font-semibold",
                                                    severityBadge(f.severity)
                                                )}
                                            >
                                                {capitalize(f.severity)}
                                            </span>
                                        </td>
                                        <td className="px-4 py-2.5 font-medium text-foreground max-w-xs truncate">
                                            {f.title}
                                        </td>
                                        <td className="px-4 py-2.5 text-muted-foreground">
                                            {f.tool_name}
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-mono">
                                            {f.mitre_technique ?? "—"}
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                            {timeAgo(f.created_at)}
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Detail slide-over */}
            {selectedFinding && (
                <FindingDetail
                    finding={selectedFinding}
                    onClose={() => setSelectedFinding(null)}
                />
            )}
        </div>
    );
}

function FindingDetail({
    finding,
    onClose,
}: {
    finding: Finding & { run_id?: string; scenario_id?: string };
    onClose: () => void;
}) {
    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            {/* Panel */}
            <div className="relative z-10 w-full max-w-lg overflow-y-auto border-l border-border bg-card p-6">
                <div className="flex items-start justify-between">
                    <div>
                        <span
                            className={cn(
                                "rounded-full px-2 py-0.5 text-xs font-semibold",
                                severityBadge(finding.severity)
                            )}
                        >
                            {capitalize(finding.severity)}
                        </span>
                        <h3 className="mt-2 text-lg font-bold text-foreground">
                            {finding.title}
                        </h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="rounded-md p-1 text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <div className="mt-4 space-y-4">
                    <InfoRow label="Tool" value={finding.tool_name} />
                    <InfoRow
                        label="MITRE Technique"
                        value={finding.mitre_technique ?? "—"}
                    />
                    <InfoRow label="Scenario" value={finding.scenario_id ?? "—"} />
                    <InfoRow label="Evidence Hash" value={finding.evidence_hash ?? "—"} />

                    {finding.description && (
                        <div>
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase">
                                Description
                            </h4>
                            <p className="mt-1 text-sm text-foreground whitespace-pre-wrap">
                                {finding.description}
                            </p>
                        </div>
                    )}

                    {finding.remediation && (
                        <div>
                            <h4 className="text-xs font-semibold text-muted-foreground uppercase">
                                Remediation
                            </h4>
                            <p className="mt-1 text-sm text-foreground whitespace-pre-wrap">
                                {finding.remediation}
                            </p>
                        </div>
                    )}

                    {finding.evidence &&
                        Object.keys(finding.evidence).length > 0 && (
                            <div>
                                <h4 className="text-xs font-semibold text-muted-foreground uppercase">
                                    Evidence
                                </h4>
                                <pre className="mt-1 max-h-48 overflow-auto rounded-md bg-secondary p-3 text-xs text-foreground">
                                    {JSON.stringify(finding.evidence, null, 2)}
                                </pre>
                            </div>
                        )}
                </div>
            </div>
        </div>
    );
}

function InfoRow({ label, value }: { label: string; value: string }) {
    return (
        <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium text-foreground font-mono text-xs">
                {value}
            </span>
        </div>
    );
}
