"use client";

import { useState } from "react";
import useSWR from "swr";
import { api, apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Plus, Loader2, Trash2, Star, Save } from "lucide-react";

interface ScoringRubric {
    id: string;
    name: string;
    rules: {
        default_threshold?: number;
        scenario_thresholds?: Record<string, number>;
        framework_thresholds?: Record<string, number>;
    };
    is_default: boolean;
    created_at: string;
}

const SCENARIO_IDS = [
    "prompt_injection", "jailbreak", "data_leakage", "toxicity_bias",
    "hallucination", "system_prompt_defense", "multi_turn_social_engineering",
    "rag_poisoning", "tool_abuse", "multimodal_injection", "code_execution_safety",
    "pii_handling", "content_policy_boundary", "language_crossover",
    "multi_agent_chain", "goal_hijacking",
];

export default function ScoringPage() {
    const { data: rubrics, mutate } = useSWR<ScoringRubric[]>(
        "/scoring/rubrics",
        (p: string) => apiFetch<ScoringRubric[]>(p)
    );

    const [showCreate, setShowCreate] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [formName, setFormName] = useState("");
    const [formDefault, setFormDefault] = useState(false);
    const [formThreshold, setFormThreshold] = useState(0.6);
    const [formScenario, setFormScenario] = useState<Record<string, number>>({});
    const [saving, setSaving] = useState(false);

    function startCreate() {
        setEditingId(null);
        setFormName("");
        setFormDefault(false);
        setFormThreshold(0.6);
        setFormScenario({});
        setShowCreate(true);
    }

    function startEdit(rubric: ScoringRubric) {
        setEditingId(rubric.id);
        setFormName(rubric.name);
        setFormDefault(rubric.is_default);
        setFormThreshold(rubric.rules.default_threshold ?? 0.6);
        setFormScenario(rubric.rules.scenario_thresholds ?? {});
        setShowCreate(true);
    }

    async function handleSave() {
        setSaving(true);
        const body = {
            name: formName,
            is_default: formDefault,
            rules: {
                default_threshold: formThreshold,
                scenario_thresholds: formScenario,
            },
        };
        try {
            if (editingId) {
                await api.put(`/scoring/rubrics/${editingId}`, body);
            } else {
                await api.post("/scoring/rubrics", body);
            }
            mutate();
            setShowCreate(false);
        } catch {
            alert("Failed to save rubric.");
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Delete this rubric?")) return;
        try {
            await api.delete(`/scoring/rubrics/${id}`);
            mutate();
        } catch {
            alert("Failed to delete rubric.");
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-foreground">Scoring Rubrics</h2>
                    <p className="text-sm text-muted-foreground">
                        Define custom pass/fail thresholds per scenario
                    </p>
                </div>
                <button
                    onClick={startCreate}
                    className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
                >
                    <Plus className="h-4 w-4" /> New Rubric
                </button>
            </div>

            {/* Create/Edit form */}
            {showCreate && (
                <div className="rounded-xl border border-border bg-card p-4 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-foreground">
                            {editingId ? "Edit Rubric" : "New Rubric"}
                        </h3>
                        <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">&times;</button>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <div>
                            <label className="text-xs font-medium text-muted-foreground">Name</label>
                            <input
                                value={formName}
                                onChange={(e) => setFormName(e.target.value)}
                                placeholder="e.g. Strict Production"
                                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-medium text-muted-foreground">
                                Default Threshold (0.0 - 1.0)
                            </label>
                            <div className="mt-1 flex items-center gap-2">
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.05"
                                    value={formThreshold}
                                    onChange={(e) => setFormThreshold(parseFloat(e.target.value))}
                                    className="flex-1"
                                />
                                <span className="w-12 text-right font-mono text-sm text-foreground">
                                    {formThreshold.toFixed(2)}
                                </span>
                            </div>
                        </div>
                    </div>
                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                        <input
                            type="checkbox"
                            checked={formDefault}
                            onChange={(e) => setFormDefault(e.target.checked)}
                            className="rounded"
                        />
                        Set as default rubric
                    </label>

                    <div>
                        <p className="text-xs font-medium text-muted-foreground mb-2">
                            Per-Scenario Overrides (leave blank to use default)
                        </p>
                        <div className="grid grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-3">
                            {SCENARIO_IDS.map((sid) => (
                                <div key={sid} className="flex items-center gap-2">
                                    <span className="w-40 truncate text-xs text-muted-foreground">{sid}</span>
                                    <input
                                        type="number"
                                        min="0"
                                        max="1"
                                        step="0.05"
                                        value={formScenario[sid] ?? ""}
                                        onChange={(e) => {
                                            const val = e.target.value;
                                            const next = { ...formScenario };
                                            if (val === "") {
                                                delete next[sid];
                                            } else {
                                                next[sid] = parseFloat(val);
                                            }
                                            setFormScenario(next);
                                        }}
                                        placeholder={formThreshold.toFixed(2)}
                                        className="w-20 rounded-md border border-border bg-background px-2 py-1 text-xs font-mono text-foreground"
                                    />
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleSave}
                        disabled={saving || !formName.trim()}
                        className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                    >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        {editingId ? "Update" : "Create"} Rubric
                    </button>
                </div>
            )}

            {/* Rubric list */}
            <div className="rounded-xl border border-border bg-card">
                <div className="border-b border-border px-4 py-3">
                    <h3 className="text-sm font-semibold text-foreground">
                        Rubrics ({(rubrics ?? []).length})
                    </h3>
                </div>
                {(rubrics ?? []).length === 0 ? (
                    <div className="px-4 py-12 text-center text-sm text-muted-foreground">
                        No custom rubrics yet. The default threshold is 0.6 (60%).
                    </div>
                ) : (
                    <div className="divide-y divide-border">
                        {(rubrics ?? []).map((r) => (
                            <div key={r.id} className="flex items-center gap-3 px-4 py-3 hover:bg-secondary/50 transition-colors">
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium text-foreground">{r.name}</span>
                                        {r.is_default && (
                                            <span className="flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                                                <Star className="h-2.5 w-2.5" /> DEFAULT
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Threshold: {r.rules.default_threshold ?? 0.6}
                                        {Object.keys(r.rules.scenario_thresholds ?? {}).length > 0 && (
                                            <> · {Object.keys(r.rules.scenario_thresholds ?? {}).length} scenario override(s)</>
                                        )}
                                    </p>
                                </div>
                                <button
                                    onClick={() => startEdit(r)}
                                    className="rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    Edit
                                </button>
                                <button
                                    onClick={() => handleDelete(r.id)}
                                    className="rounded-md p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
