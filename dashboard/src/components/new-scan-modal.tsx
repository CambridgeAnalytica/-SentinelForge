"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, apiFetch } from "@/lib/api";
import { mutate } from "swr";
import { X, Play } from "lucide-react";

interface Scenario {
    id: string;
    name: string;
    description: string;
    tools: string[];
}

interface Props {
    onClose: () => void;
}

export function NewScanModal({ onClose }: Props) {
    const router = useRouter();
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [scenarioId, setScenarioId] = useState("");
    const [targetModel, setTargetModel] = useState("llama3.2:3b");
    const [multiTurn, setMultiTurn] = useState(true);
    const [maxTurns, setMaxTurns] = useState(10);
    const [provider, setProvider] = useState("openai");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        apiFetch<Scenario[]>("/attacks/scenarios")
            .then((data) => {
                setScenarios(data ?? []);
                if (data?.length > 0) setScenarioId(data[0].id);
            })
            .catch(() => {});
    }, []);

    const selected = scenarios.find((s) => s.id === scenarioId);

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        setError("");
        if (!scenarioId) {
            setError("Select a scenario");
            return;
        }
        if (!targetModel.trim()) {
            setError("Enter a target model");
            return;
        }
        setLoading(true);
        try {
            const config: Record<string, unknown> = {};
            if (multiTurn) {
                config.multi_turn = true;
                config.max_turns = maxTurns;
                config.provider = provider;
            }
            const result = await api.post<{ id: string }>("/attacks/run", {
                scenario_id: scenarioId,
                target_model: targetModel.trim(),
                config,
            });
            mutate("/attacks/runs");
            onClose();
            router.push(`/attacks/${result.id}`);
        } catch {
            setError("Failed to launch scan. Check API logs.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />
            <div className="relative z-10 w-full max-w-lg rounded-xl border border-border bg-card p-6">
                <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-bold text-foreground">New Scan</h3>
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

                    <Field label="Scenario">
                        <select
                            value={scenarioId}
                            onChange={(e) => setScenarioId(e.target.value)}
                            required
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                            <option value="">Select a scenario...</option>
                            {scenarios.map((s) => (
                                <option key={s.id} value={s.id}>
                                    {s.name}
                                </option>
                            ))}
                        </select>
                    </Field>

                    {selected && (
                        <p className="text-xs text-muted-foreground">
                            {selected.description?.slice(0, 150)}
                            {selected.tools.length > 0 && (
                                <span className="ml-1">
                                    Tools: {selected.tools.join(", ")}
                                </span>
                            )}
                        </p>
                    )}

                    <Field label="Target Model">
                        <input
                            value={targetModel}
                            onChange={(e) => setTargetModel(e.target.value)}
                            required
                            placeholder="llama3.2:3b"
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </Field>

                    <Field label="Provider">
                        <select
                            value={provider}
                            onChange={(e) => setProvider(e.target.value)}
                            className="flex h-9 w-full rounded-md border border-input bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        >
                            <option value="openai">OpenAI / Ollama (local)</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="azure_openai">Azure OpenAI</option>
                            <option value="bedrock">AWS Bedrock</option>
                        </select>
                    </Field>

                    <div className="flex items-center gap-3">
                        <input
                            type="checkbox"
                            id="multi-turn"
                            checked={multiTurn}
                            onChange={(e) => setMultiTurn(e.target.checked)}
                            className="h-4 w-4 rounded border-input"
                        />
                        <label htmlFor="multi-turn" className="text-sm text-foreground">
                            Enable multi-turn adversarial mode
                        </label>
                    </div>

                    {multiTurn && (
                        <Field label={`Max turns: ${maxTurns}`}>
                            <input
                                type="range"
                                min={3}
                                max={20}
                                value={maxTurns}
                                onChange={(e) => setMaxTurns(Number(e.target.value))}
                                className="w-full accent-primary"
                            />
                            <div className="flex justify-between text-[10px] text-muted-foreground">
                                <span>3</span>
                                <span>10</span>
                                <span>20</span>
                            </div>
                        </Field>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                    >
                        <Play className="h-4 w-4" />
                        {loading ? "Launching..." : "Launch Scan"}
                    </button>
                </form>
            </div>
        </div>
    );
}

function Field({
    label,
    children,
}: {
    label: string;
    children: React.ReactNode;
}) {
    return (
        <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">{label}</label>
            {children}
        </div>
    );
}
