"use client";

import { useState, useEffect, useCallback } from "react";
import { Swords, Plus, Trash2, Save, Eye, Code, X, Shield, Repeat, FileText } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Scenario {
    id: string;
    name: string;
    description: string;
    severity: string;
    category: string;
    tools: string[];
    mitre_techniques: string[];
    owasp_llm: string[];
    test_cases_count: number;
    prompt_count: number;
    multi_turn: boolean;
    config: Record<string, unknown>;
    custom?: boolean;
    created_by?: string;
}

const EMPTY_SCENARIO: Scenario = {
    id: "",
    name: "",
    description: "",
    severity: "medium",
    category: "general",
    tools: [],
    mitre_techniques: [],
    owasp_llm: [],
    test_cases_count: 0,
    prompt_count: 0,
    multi_turn: false,
    config: {},
};

const SEVERITY_STYLES: Record<string, string> = {
    critical: "bg-red-500/20 text-red-300 border-red-500/30",
    high: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    medium: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    low: "bg-green-500/20 text-green-300 border-green-500/30",
    info: "bg-blue-500/20 text-blue-300 border-blue-500/30",
};

const CATEGORY_STYLES: Record<string, string> = {
    injection: "bg-red-500/10 text-red-400",
    jailbreak: "bg-purple-500/10 text-purple-400",
    safety: "bg-amber-500/10 text-amber-400",
    privacy: "bg-cyan-500/10 text-cyan-400",
    accuracy: "bg-teal-500/10 text-teal-400",
    general: "bg-zinc-500/10 text-zinc-400",
};

export default function ScenariosPage() {
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState<Scenario | null>(null);
    const [isNew, setIsNew] = useState(false);
    const [toolInput, setToolInput] = useState("");
    const [mitreInput, setMitreInput] = useState("");
    const [configText, setConfigText] = useState("{}");
    const [preview, setPreview] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [availableTools, setAvailableTools] = useState<string[]>([]);

    const token = () => localStorage.getItem("sf_token") ?? "";

    const fetchScenarios = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API}/attacks/scenarios`, {
                headers: { Authorization: `Bearer ${token()}` },
            });
            if (res.ok) setScenarios(await res.json());
        } catch { /* ignore */ }
        setLoading(false);
    }, []);

    useEffect(() => {
        fetchScenarios();
        // Fetch available tools
        fetch(`${API}/tools`, {
            headers: { Authorization: `Bearer ${token()}` },
        })
            .then((r) => r.json())
            .then((data) => setAvailableTools((data ?? []).map((t: { name: string }) => t.name)))
            .catch(() => { });
    }, [fetchScenarios]);

    const startCreate = () => {
        setEditing({ ...EMPTY_SCENARIO });
        setIsNew(true);
        setConfigText("{}");
        setError("");
    };

    const startEdit = (s: Scenario) => {
        setEditing({ ...s });
        setIsNew(false);
        setConfigText(JSON.stringify(s.config, null, 2));
        setError("");
    };

    const save = async () => {
        if (!editing) return;
        setSaving(true);
        setError("");

        let parsedConfig = {};
        try {
            parsedConfig = JSON.parse(configText);
        } catch {
            setError("Invalid JSON in config");
            setSaving(false);
            return;
        }

        const body = { ...editing, config: parsedConfig };

        try {
            const url = isNew ? `${API}/attacks/scenarios` : `${API}/attacks/scenarios/${editing.id}`;
            const method = isNew ? "POST" : "PUT";
            const res = await fetch(url, {
                method,
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token()}`,
                },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const data = await res.json();
                setError(data.detail || "Failed to save");
            } else {
                setEditing(null);
                fetchScenarios();
            }
        } catch (e) {
            setError("Network error");
        }
        setSaving(false);
    };

    const del = async (id: string) => {
        if (!confirm(`Delete scenario "${id}"?`)) return;
        await fetch(`${API}/attacks/scenarios/${id}`, {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token()}` },
        });
        fetchScenarios();
    };

    const addTool = () => {
        if (!editing || !toolInput.trim()) return;
        if (!editing.tools.includes(toolInput.trim())) {
            setEditing({ ...editing, tools: [...editing.tools, toolInput.trim()] });
        }
        setToolInput("");
    };

    const removeTool = (t: string) => {
        if (!editing) return;
        setEditing({ ...editing, tools: editing.tools.filter((x) => x !== t) });
    };

    const addMitre = () => {
        if (!editing || !mitreInput.trim()) return;
        if (!editing.mitre_techniques.includes(mitreInput.trim())) {
            setEditing({ ...editing, mitre_techniques: [...editing.mitre_techniques, mitreInput.trim()] });
        }
        setMitreInput("");
    };

    const removeMitre = (t: string) => {
        if (!editing) return;
        setEditing({ ...editing, mitre_techniques: editing.mitre_techniques.filter((x) => x !== t) });
    };

    const toYaml = (s: Scenario) => {
        let y = `id: ${s.id}\nname: ${s.name}\ndescription: ${s.description}\ntools:\n`;
        s.tools.forEach((t) => (y += `  - ${t}\n`));
        if (s.mitre_techniques.length) {
            y += "mitre_techniques:\n";
            s.mitre_techniques.forEach((t) => (y += `  - ${t}\n`));
        }
        if (Object.keys(s.config).length) {
            y += `config: ${JSON.stringify(s.config, null, 2)}\n`;
        }
        return y;
    };

    const totalPrompts = scenarios.reduce((acc, s) => acc + s.prompt_count, 0);
    const totalTestCases = scenarios.reduce((acc, s) => acc + s.test_cases_count, 0);

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <Swords className="h-6 w-6 text-primary" />
                <h2 className="text-2xl font-bold">Scenario Builder</h2>
                <button
                    onClick={startCreate}
                    className="ml-auto flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                    <Plus className="h-4 w-4" /> New Scenario
                </button>
            </div>

            {/* Summary Stats */}
            {!loading && scenarios.length > 0 && (
                <div className="grid grid-cols-4 gap-3">
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-center">
                        <div className="text-2xl font-bold text-primary">{scenarios.length}</div>
                        <div className="text-xs text-zinc-500">Scenarios</div>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-center">
                        <div className="text-2xl font-bold text-blue-400">{totalTestCases}</div>
                        <div className="text-xs text-zinc-500">Test Cases</div>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-center">
                        <div className="text-2xl font-bold text-emerald-400">{totalPrompts}</div>
                        <div className="text-xs text-zinc-500">Prompts</div>
                    </div>
                    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-center">
                        <div className="text-2xl font-bold text-purple-400">{scenarios.filter(s => s.multi_turn).length}</div>
                        <div className="text-xs text-zinc-500">Multi-Turn</div>
                    </div>
                </div>
            )}

            {/* Editor Panel */}
            {editing && (
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold">{isNew ? "Create Scenario" : `Edit: ${editing.name}`}</h3>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPreview(!preview)}
                                className="flex items-center gap-1 rounded px-3 py-1.5 text-xs border border-zinc-700 hover:bg-zinc-800"
                            >
                                {preview ? <Code className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                                {preview ? "Editor" : "YAML Preview"}
                            </button>
                            <button onClick={() => setEditing(null)} className="text-zinc-500 hover:text-zinc-300"><X className="h-4 w-4" /></button>
                        </div>
                    </div>

                    {preview ? (
                        <pre className="bg-zinc-950 rounded-lg p-4 text-sm font-mono text-emerald-400 overflow-x-auto">
                            {toYaml(editing)}
                        </pre>
                    ) : (
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-zinc-500 mb-1 block">ID</label>
                                <input
                                    className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm"
                                    value={editing.id}
                                    onChange={(e) => setEditing({ ...editing, id: e.target.value })}
                                    disabled={!isNew}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-zinc-500 mb-1 block">Name</label>
                                <input
                                    className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm"
                                    value={editing.name}
                                    onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                                />
                            </div>
                            <div className="col-span-2">
                                <label className="text-xs text-zinc-500 mb-1 block">Description</label>
                                <textarea
                                    className="w-full rounded border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm h-20 resize-none"
                                    value={editing.description}
                                    onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                                />
                            </div>
                            <div>
                                <label className="text-xs text-zinc-500 mb-1 block">Tools</label>
                                <div className="flex gap-2 mb-2">
                                    <select
                                        className="flex-1 rounded border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm"
                                        value={toolInput}
                                        onChange={(e) => setToolInput(e.target.value)}
                                    >
                                        <option value="">Select tool...</option>
                                        {availableTools.map((t) => (
                                            <option key={t} value={t}>{t}</option>
                                        ))}
                                    </select>
                                    <button onClick={addTool} className="rounded bg-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-600">Add</button>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                    {editing.tools.map((t) => (
                                        <span key={t} className="flex items-center gap-1 rounded-full bg-blue-500/20 text-blue-300 px-2.5 py-0.5 text-xs">
                                            {t}
                                            <button onClick={() => removeTool(t)}><X className="h-3 w-3" /></button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label className="text-xs text-zinc-500 mb-1 block">MITRE Techniques</label>
                                <div className="flex gap-2 mb-2">
                                    <input
                                        className="flex-1 rounded border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm"
                                        placeholder="e.g. AML.T0043"
                                        value={mitreInput}
                                        onChange={(e) => setMitreInput(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && addMitre()}
                                    />
                                    <button onClick={addMitre} className="rounded bg-zinc-700 px-3 py-1.5 text-xs hover:bg-zinc-600">Add</button>
                                </div>
                                <div className="flex flex-wrap gap-1">
                                    {editing.mitre_techniques.map((t) => (
                                        <span key={t} className="flex items-center gap-1 rounded-full bg-orange-500/20 text-orange-300 px-2.5 py-0.5 text-xs">
                                            {t}
                                            <button onClick={() => removeMitre(t)}><X className="h-3 w-3" /></button>
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <div className="col-span-2">
                                <label className="text-xs text-zinc-500 mb-1 block">Config (JSON)</label>
                                <textarea
                                    className="w-full rounded border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm font-mono h-28 resize-none"
                                    value={configText}
                                    onChange={(e) => setConfigText(e.target.value)}
                                />
                            </div>
                        </div>
                    )}

                    {error && <p className="text-sm text-red-400">{error}</p>}

                    <div className="flex justify-end gap-2">
                        <button onClick={() => setEditing(null)} className="rounded px-4 py-2 text-sm border border-zinc-700 hover:bg-zinc-800">Cancel</button>
                        <button onClick={save} disabled={saving} className="flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                            <Save className="h-4 w-4" /> {saving ? "Saving..." : "Save"}
                        </button>
                    </div>
                </div>
            )}

            {/* Scenario List */}
            <div className="grid gap-4">
                {loading && <p className="text-zinc-500 text-center py-8">Loading scenarios...</p>}
                {!loading && scenarios.length === 0 && <p className="text-zinc-500 text-center py-8">No scenarios found</p>}
                {!loading && scenarios.map((s) => (
                    <div key={s.id} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 hover:border-zinc-700 transition-colors">
                        <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <h3 className="font-semibold">{s.name}</h3>
                                    <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs font-mono text-zinc-400">{s.id}</span>
                                    <span className={`rounded border px-2 py-0.5 text-xs font-medium ${SEVERITY_STYLES[s.severity] || SEVERITY_STYLES.medium}`}>
                                        {s.severity}
                                    </span>
                                    <span className={`rounded px-2 py-0.5 text-xs ${CATEGORY_STYLES[s.category] || CATEGORY_STYLES.general}`}>
                                        {s.category}
                                    </span>
                                    {s.multi_turn && (
                                        <span className="flex items-center gap-1 rounded bg-purple-500/15 text-purple-300 px-2 py-0.5 text-xs">
                                            <Repeat className="h-3 w-3" /> multi-turn
                                        </span>
                                    )}
                                    {s.custom && <span className="rounded bg-purple-500/20 text-purple-300 px-2 py-0.5 text-xs">Custom</span>}
                                </div>
                                <p className="mt-1 text-sm text-zinc-400">{s.description}</p>
                                <div className="mt-3 flex flex-wrap items-center gap-3">
                                    {/* Stats */}
                                    <div className="flex items-center gap-1.5 text-xs text-zinc-500">
                                        <FileText className="h-3.5 w-3.5" />
                                        <span>{s.test_cases_count} test cases</span>
                                        <span className="text-zinc-700">|</span>
                                        <span>{s.prompt_count} prompts</span>
                                    </div>
                                    <div className="text-zinc-800">|</div>
                                    {/* Tools */}
                                    <div className="flex flex-wrap gap-1.5">
                                        {s.tools.map((t) => (
                                            <span key={t} className="rounded bg-blue-500/10 text-blue-400 px-2 py-0.5 text-xs">{t}</span>
                                        ))}
                                    </div>
                                </div>
                                {/* MITRE + OWASP tags */}
                                {(s.mitre_techniques.length > 0 || s.owasp_llm.length > 0) && (
                                    <div className="mt-2 flex flex-wrap gap-1.5">
                                        {s.mitre_techniques.map((t) => (
                                            <span key={t} className="rounded bg-orange-500/10 text-orange-400 px-2 py-0.5 text-xs">{t}</span>
                                        ))}
                                        {s.owasp_llm.map((t) => (
                                            <span key={t} className="flex items-center gap-1 rounded bg-rose-500/10 text-rose-400 px-2 py-0.5 text-xs">
                                                <Shield className="h-3 w-3" /> {t}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                            {s.custom && (
                                <div className="flex gap-1 ml-3">
                                    <button
                                        onClick={() => startEdit(s)}
                                        className="rounded p-1.5 hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300"
                                    >
                                        <Code className="h-4 w-4" />
                                    </button>
                                    <button
                                        onClick={() => del(s.id)}
                                        className="rounded p-1.5 hover:bg-zinc-800 text-zinc-500 hover:text-red-400"
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
