"use client";

import { useState } from "react";
import { useReports, useAttackRuns } from "@/hooks/use-api";
import { api } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";
import { FileText, Download, Plus, X, Eye, Loader2 } from "lucide-react";
import { mutate } from "swr";

export default function ReportsPage() {
    const { data: reports, isLoading } = useReports();
    const [showGenerate, setShowGenerate] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
                <div className="h-96 animate-pulse rounded-xl bg-secondary" />
            </div>
        );
    }

    const allReports = reports ?? [];

    async function handleDownload(id: string, format: string) {
        const blob = await api.get<Blob>(`/reports/${id}/download`);
        const url = URL.createObjectURL(blob as Blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `report_${id}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
    }

    function handlePreview(id: string) {
        const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        setPreviewUrl(`${apiBase}/reports/${id}/download`);
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Reports</h2>
                    <p className="text-sm text-muted-foreground">
                        Generated security assessment reports
                    </p>
                </div>
                <button
                    onClick={() => setShowGenerate(true)}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> Generate Report
                </button>
            </div>

            {/* Report list */}
            <div className="rounded-xl border border-border bg-card">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left text-xs text-muted-foreground">
                                <th className="px-4 py-2 font-medium">Run ID</th>
                                <th className="px-4 py-2 font-medium">Format</th>
                                <th className="px-4 py-2 font-medium">Generated</th>
                                <th className="px-4 py-2 font-medium">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {allReports.length === 0 ? (
                                <tr>
                                    <td
                                        colSpan={4}
                                        className="px-4 py-12 text-center text-muted-foreground"
                                    >
                                        <FileText className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
                                        No reports generated yet.
                                    </td>
                                </tr>
                            ) : (
                                allReports.map((r) => (
                                    <tr
                                        key={r.id}
                                        className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors"
                                    >
                                        <td className="px-4 py-2.5 font-mono text-xs text-foreground">
                                            {r.run_id}
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <span className="rounded bg-secondary px-2 py-0.5 text-xs font-medium text-foreground uppercase">
                                                {r.format}
                                            </span>
                                        </td>
                                        <td className="px-4 py-2.5 text-xs text-muted-foreground">
                                            {timeAgo(r.generated_at)}
                                        </td>
                                        <td className="px-4 py-2.5">
                                            <div className="flex gap-1">
                                                {(r.format === "html" || r.format === "pdf") && (
                                                    <button
                                                        onClick={() => handlePreview(r.id)}
                                                        className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                                                        title="Preview"
                                                    >
                                                        <Eye className="h-3.5 w-3.5" />
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDownload(r.id, r.format)}
                                                    className="rounded p-1 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                                                    title="Download"
                                                >
                                                    <Download className="h-3.5 w-3.5" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Preview modal */}
            {previewUrl && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div
                        className="absolute inset-0 bg-black/50"
                        onClick={() => setPreviewUrl(null)}
                    />
                    <div className="relative z-10 h-[85vh] w-[80vw] overflow-hidden rounded-xl border border-border bg-card">
                        <div className="flex h-10 items-center justify-between border-b border-border px-4">
                            <span className="text-sm font-medium text-foreground">
                                Report Preview
                            </span>
                            <button
                                onClick={() => setPreviewUrl(null)}
                                className="text-muted-foreground hover:text-foreground"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                        <iframe
                            src={previewUrl}
                            className="h-full w-full border-0"
                            title="Report preview"
                        />
                    </div>
                </div>
            )}

            {/* Generate modal */}
            {showGenerate && (
                <GenerateReportModal onClose={() => setShowGenerate(false)} />
            )}
        </div>
    );
}

function GenerateReportModal({ onClose }: { onClose: () => void }) {
    const { data: runs } = useAttackRuns();
    const [runId, setRunId] = useState("");
    const [formats, setFormats] = useState<string[]>(["html"]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const completedRuns = (runs ?? []).filter((r) => r.status === "completed");

    function toggleFormat(fmt: string) {
        setFormats((prev) =>
            prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
        );
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await api.post("/reports/generate", {
                run_id: runId,
                formats,
            });
            mutate("/reports");
            onClose();
        } catch {
            setError("Failed to generate report");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-lg rounded-xl border border-border bg-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-foreground">Generate Report</h3>
                    <button
                        onClick={onClose}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {error && (
                        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                            {error}
                        </div>
                    )}

                    <div className="space-y-1">
                        <label className="text-sm font-medium text-foreground">
                            Select Completed Scan
                        </label>
                        {completedRuns.length > 0 ? (
                            <select
                                value={runId}
                                onChange={(e) => setRunId(e.target.value)}
                                required
                                className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring appearance-none"
                            >
                                <option value="">Choose a scan...</option>
                                {completedRuns.map((r) => (
                                    <option key={r.id} value={r.id}>
                                        {r.scenario_id} &mdash; {r.target_model} ({(r.findings ?? []).length} findings) &mdash; {r.id.slice(0, 8)}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <p className="text-sm text-muted-foreground py-2">
                                No completed scans available. Run an attack first.
                            </p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                            Formats
                        </label>
                        <div className="flex gap-2">
                            {["html", "pdf", "jsonl"].map((fmt) => (
                                <button
                                    type="button"
                                    key={fmt}
                                    onClick={() => toggleFormat(fmt)}
                                    className={cn(
                                        "rounded-md border px-3 py-1.5 text-xs font-medium uppercase transition-colors",
                                        formats.includes(fmt)
                                            ? "border-primary bg-primary/10 text-primary"
                                            : "border-input bg-secondary text-muted-foreground hover:text-foreground"
                                    )}
                                >
                                    {fmt}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading || formats.length === 0 || !runId}
                        className="flex h-10 w-full items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                        {loading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            "Generate"
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
