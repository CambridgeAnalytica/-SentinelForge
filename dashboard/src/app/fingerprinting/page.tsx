"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { useFingerprintRuns, useFingerprintDetail } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import {
    Fingerprint,
    Play,
    Loader2,
    CheckCircle2,
    XCircle,
    ChevronDown,
    ChevronRight,
} from "lucide-react";
import {
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    ResponsiveContainer,
} from "recharts";

const STATUS_ICON: Record<string, React.ReactNode> = {
    completed: <CheckCircle2 className="h-4 w-4 text-green-400" />,
    running: <Loader2 className="h-4 w-4 animate-spin text-blue-400" />,
    queued: <Loader2 className="h-4 w-4 text-yellow-400" />,
    failed: <XCircle className="h-4 w-4 text-red-400" />,
};

const CATEGORIES = [
    { value: "identity", label: "Identity" },
    { value: "safety", label: "Safety / Refusal" },
    { value: "cutoff", label: "Knowledge Cutoff" },
    { value: "compliance", label: "Instruction Compliance" },
    { value: "style", label: "Style Quirks" },
    { value: "technical", label: "Technical Knowledge" },
];

const PROVIDERS = [
    { value: "ollama", label: "Ollama (Local)" },
    { value: "openai", label: "OpenAI" },
    { value: "anthropic", label: "Anthropic" },
    { value: "azure_openai", label: "Azure OpenAI" },
    { value: "bedrock", label: "AWS Bedrock" },
    { value: "custom", label: "Custom Gateway" },
];

const REQUEST_TEMPLATES = [
    { value: "openai", label: "OpenAI-compatible" },
    { value: "anthropic", label: "Anthropic-compatible" },
    { value: "cohere", label: "Cohere Command R" },
    { value: "google", label: "Google Gemini / Vertex AI" },
    { value: "raw", label: "Raw JSON" },
];

export default function FingerprintingPage() {
    const { data: runs, mutate } = useFingerprintRuns();
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const { data: detail } = useFingerprintDetail(selectedId);
    const [provider, setProvider] = useState("ollama");
    const [endpoint, setEndpoint] = useState("");
    const [model, setModel] = useState("unknown");
    const [requestTemplate, setRequestTemplate] = useState("openai");
    const [selectedCategories, setSelectedCategories] = useState<string[]>(["all"]);
    const [launching, setLaunching] = useState(false);
    const [expandedProbes, setExpandedProbes] = useState<Set<number>>(new Set());

    const toggleCategory = (cat: string) => {
        if (cat === "all") {
            setSelectedCategories(["all"]);
            return;
        }
        setSelectedCategories((prev) => {
            const without = prev.filter((c) => c !== "all" && c !== cat);
            if (prev.includes(cat)) {
                return without.length === 0 ? ["all"] : without;
            }
            return [...without, cat];
        });
    };

    const handleLaunch = async () => {
        setLaunching(true);
        try {
            const config: Record<string, unknown> = {};
            if (endpoint.trim()) config.base_url = endpoint.trim();
            if (provider === "custom") {
                config.request_template = requestTemplate;
            }

            const result = await apiFetch<{ id: string }>("/fingerprint/run", {
                method: "POST",
                body: JSON.stringify({
                    target_model: model,
                    provider,
                    config,
                    probe_categories: selectedCategories,
                }),
            });
            setSelectedId(result.id);
            mutate();
        } catch (e) {
            console.error("Fingerprint launch failed:", e);
        } finally {
            setLaunching(false);
        }
    };

    const results = (detail?.results as Record<string, unknown>) ?? {};
    const topMatches = (results.top_matches as { model: string; family: string; confidence: number; category_scores: Record<string, number> }[]) ?? [];
    const categoryScores = (results.category_scores as Record<string, number>) ?? {};
    const profile = (results.behavioral_profile as string) ?? "";
    const probeResults = (results.probe_results as { probe_id: string; category: string; prompt: string; response_excerpt: string; features: Record<string, unknown> }[]) ?? [];

    // Radar chart data
    const radarData = Object.entries(categoryScores).map(([cat, score]) => ({
        category: cat.charAt(0).toUpperCase() + cat.slice(1),
        score: Math.round(score * 100),
    }));

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Fingerprint className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">Model Fingerprinting</h1>
            </div>

            <p className="text-sm text-muted-foreground">
                Identify unknown LLMs behind black-box endpoints. Sends 22 behavioral probes
                across 6 categories and matches response patterns against 16 known model
                signatures to determine the target model with confidence scores.
            </p>

            {/* Launch form */}
            <div className="rounded-lg border bg-card p-4 space-y-4">
                <h2 className="font-semibold">Run Fingerprint Scan</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                        <label className="text-sm text-muted-foreground">Provider</label>
                        <select
                            value={provider}
                            onChange={(e) => setProvider(e.target.value)}
                            className="mt-1 block w-full rounded border bg-background px-3 py-2 text-sm"
                        >
                            {PROVIDERS.map((p) => (
                                <option key={p.value} value={p.value}>{p.label}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground">Target Endpoint</label>
                        <input
                            value={endpoint}
                            onChange={(e) => setEndpoint(e.target.value)}
                            placeholder="https://target.example.com/v1"
                            className="mt-1 block w-full rounded border bg-background px-3 py-2 text-sm"
                        />
                    </div>
                    <div>
                        <label className="text-sm text-muted-foreground">Model Name (if known)</label>
                        <input
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            placeholder="unknown"
                            className="mt-1 block w-full rounded border bg-background px-3 py-2 text-sm"
                        />
                    </div>
                </div>

                {provider === "custom" && (
                    <div>
                        <label className="text-sm text-muted-foreground">Request Format</label>
                        <select
                            value={requestTemplate}
                            onChange={(e) => setRequestTemplate(e.target.value)}
                            className="mt-1 block w-48 rounded border bg-background px-3 py-2 text-sm"
                        >
                            {REQUEST_TEMPLATES.map((t) => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                            ))}
                        </select>
                    </div>
                )}

                <div>
                    <label className="text-sm text-muted-foreground mb-2 block">Probe Categories</label>
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={() => toggleCategory("all")}
                            className={cn(
                                "rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                                selectedCategories.includes("all")
                                    ? "bg-primary text-primary-foreground border-primary"
                                    : "border-border hover:bg-muted"
                            )}
                        >
                            All (22 probes)
                        </button>
                        {CATEGORIES.map((cat) => (
                            <button
                                key={cat.value}
                                onClick={() => toggleCategory(cat.value)}
                                className={cn(
                                    "rounded-full px-3 py-1 text-xs font-medium border transition-colors",
                                    selectedCategories.includes(cat.value)
                                        ? "bg-primary text-primary-foreground border-primary"
                                        : "border-border hover:bg-muted"
                                )}
                            >
                                {cat.label}
                            </button>
                        ))}
                    </div>
                </div>

                <button
                    onClick={handleLaunch}
                    disabled={launching}
                    className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                    {launching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    Launch Fingerprint Scan
                </button>
            </div>

            {/* Results */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Run list */}
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
                    {detail && detail.status === "completed" && topMatches.length > 0 && (
                        <>
                            {/* Top matches */}
                            <div className="rounded-lg border bg-card p-4 space-y-3">
                                <h3 className="font-semibold">Model Identification</h3>
                                {topMatches.map((match, i) => (
                                    <div key={i} className="flex items-center gap-3">
                                        <span className={cn(
                                            "flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold",
                                            i === 0 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                                        )}>
                                            {i + 1}
                                        </span>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium">{match.model}</span>
                                                <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                                    {match.family}
                                                </span>
                                            </div>
                                            <div className="mt-1 h-2 rounded-full bg-muted overflow-hidden">
                                                <div
                                                    className={cn(
                                                        "h-full rounded-full transition-all",
                                                        match.confidence >= 0.7 ? "bg-green-500" :
                                                        match.confidence >= 0.5 ? "bg-yellow-500" : "bg-red-500"
                                                    )}
                                                    style={{ width: `${match.confidence * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                        <span className="text-sm font-bold tabular-nums">
                                            {Math.round(match.confidence * 100)}%
                                        </span>
                                    </div>
                                ))}
                            </div>

                            {/* Radar chart + Profile */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {radarData.length > 0 && (
                                    <div className="rounded-lg border bg-card p-4">
                                        <h3 className="font-semibold mb-2">Category Scores</h3>
                                        <ResponsiveContainer width="100%" height={250}>
                                            <RadarChart data={radarData}>
                                                <PolarGrid stroke="#333" />
                                                <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: "#999" }} />
                                                <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#666" }} />
                                                <Radar
                                                    name="Score"
                                                    dataKey="score"
                                                    stroke="#6366f1"
                                                    fill="#6366f1"
                                                    fillOpacity={0.3}
                                                />
                                            </RadarChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}

                                <div className="rounded-lg border bg-card p-4">
                                    <h3 className="font-semibold mb-2">Behavioral Profile</h3>
                                    <p className="text-sm text-muted-foreground leading-relaxed">
                                        {profile || "No profile generated."}
                                    </p>
                                </div>
                            </div>

                            {/* Per-probe results */}
                            <div className="rounded-lg border bg-card p-4 space-y-2">
                                <h3 className="font-semibold">Probe Results ({probeResults.length} probes)</h3>
                                {probeResults.map((pr, i) => {
                                    const expanded = expandedProbes.has(i);
                                    return (
                                        <div key={i} className="border rounded p-3">
                                            <button
                                                onClick={() => {
                                                    const next = new Set(expandedProbes);
                                                    expanded ? next.delete(i) : next.add(i);
                                                    setExpandedProbes(next);
                                                }}
                                                className="flex items-center gap-2 w-full text-left text-sm"
                                            >
                                                {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                                                <span className="rounded bg-muted px-2 py-0.5 text-xs">{pr.category}</span>
                                                <span className="font-medium flex-1">{pr.probe_id}</span>
                                            </button>
                                            {expanded && (
                                                <div className="mt-2 space-y-2">
                                                    <div>
                                                        <span className="text-xs text-muted-foreground">Prompt:</span>
                                                        <p className="text-sm bg-muted/30 rounded p-2 mt-1">
                                                            {pr.prompt || "(empty)"}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <span className="text-xs text-muted-foreground">Response:</span>
                                                        <pre className="text-xs bg-muted/50 rounded p-2 mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">
                                                            {pr.response_excerpt}
                                                        </pre>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </>
                    )}

                    {detail && detail.status === "running" && (
                        <div className="flex items-center gap-2 text-sm text-blue-400">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Running... {Math.round(detail.progress * 100)}%
                        </div>
                    )}

                    {detail && detail.status === "failed" && (
                        <div className="rounded border border-red-900/50 bg-red-900/10 p-4 text-sm text-red-400">
                            Fingerprint run failed. Check API logs for details.
                        </div>
                    )}

                    {!detail && selectedId && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Loading...
                        </div>
                    )}

                    {!selectedId && (
                        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                            <Fingerprint className="h-12 w-12 mb-3 opacity-30" />
                            <p className="text-sm">Select a run to view results, or launch a new scan</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
