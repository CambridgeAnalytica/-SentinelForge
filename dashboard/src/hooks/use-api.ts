"use client";

import useSWR from "swr";
import { useState, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";

const fetcher = <T,>(path: string) => apiFetch<T>(path);
const SSE_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/* ── Attack Runs ── */

export interface AttackRun {
    id: string;
    scenario_id: string;
    target_model: string;
    status: string;
    progress: number;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    config?: Record<string, unknown>;
    results?: Record<string, unknown>;
    error_message?: string;
    findings?: Finding[];
}

export interface Finding {
    id: string;
    tool_name: string;
    severity: string;
    title: string;
    description?: string;
    mitre_technique?: string;
    evidence?: Record<string, unknown>;
    remediation?: string;
    evidence_hash?: string;
    fingerprint?: string;
    is_new?: boolean;
    false_positive?: boolean;
    created_at: string;
}

export function useAttackRuns() {
    return useSWR<AttackRun[]>("/attacks/runs", fetcher, { refreshInterval: 10000 });
}

export function useAttackRun(id: string | null) {
    return useSWR<AttackRun>(id ? `/attacks/runs/${id}` : null, fetcher);
}

export function useAttackRunDetail(id: string | null) {
    const swr = useSWR<AttackRun>(id ? `/attacks/runs/${id}` : null, fetcher, {
        refreshInterval: (data) =>
            data?.status === "running" || data?.status === "queued" ? 5000 : 0,
    });
    return swr;
}

/** SSE hook for real-time attack run progress */
export function useAttackRunSSE(runId: string | null) {
    const [progress, setProgress] = useState<{ status: string; progress: number } | null>(null);
    const [connected, setConnected] = useState(false);
    const esRef = useRef<EventSource | null>(null);

    useEffect(() => {
        if (!runId) return;
        const token = localStorage.getItem("sf_token");
        const url = `${SSE_BASE}/attacks/runs/${runId}/stream${token ? `?token=${token}` : ""}`;
        const es = new EventSource(url);
        esRef.current = es;

        es.onopen = () => setConnected(true);
        es.addEventListener("progress", (e: MessageEvent) => {
            try {
                setProgress(JSON.parse(e.data));
            } catch { /* ignore */ }
        });
        es.addEventListener("done", (e: MessageEvent) => {
            try {
                setProgress(JSON.parse(e.data));
            } catch { /* ignore */ }
            es.close();
            setConnected(false);
        });
        es.addEventListener("error", () => {
            es.close();
            setConnected(false);
        });

        return () => {
            es.close();
            setConnected(false);
        };
    }, [runId]);

    return { progress, connected };
}

/* ── Drift ── */

export interface DriftBaseline {
    id: string;
    model: string;
    test_suite: string;
    created_at: string;
    scores: Record<string, number>;
}

export interface DriftComparison {
    baseline_id: string;
    current_scores: Record<string, number>;
    deltas: Record<string, number>;
    overall_drift: number;
    degraded_categories: string[];
}

export function useDriftBaselines() {
    return useSWR<DriftBaseline[]>("/drift/baselines", fetcher);
}

export function useDriftHistory(baselineId: string | null) {
    return useSWR<DriftComparison[]>(
        baselineId ? `/drift/history/${baselineId}` : null,
        fetcher
    );
}

/* ── Schedules ── */

export interface Schedule {
    id: string;
    name: string;
    scenario_id: string;
    target_model: string;
    cron_expression: string;
    is_active: boolean;
    next_run_at?: string;
    last_run_at?: string;
    created_at: string;
}

export function useSchedules() {
    return useSWR<Schedule[]>("/schedules", fetcher, { refreshInterval: 30000 });
}

/* ── Compliance ── */

export interface ComplianceFramework {
    id: string;
    name: string;
    categories: { id: string; name: string; description: string }[];
}

export interface ComplianceSummary {
    framework_id: string;
    total_categories: number;
    covered_categories: number;
    coverage_percentage: number;
    category_coverage: Record<string, { covered: boolean; finding_count: number }>;
}

export function useComplianceFrameworks() {
    return useSWR<ComplianceFramework[]>("/compliance/frameworks", fetcher);
}

/* ── Reports ── */

export interface Report {
    id: string;
    run_id: string;
    format: string;
    file_path?: string;
    s3_key?: string;
    generated_at: string;
}

export function useReports() {
    return useSWR<Report[]>("/reports", fetcher);
}

/* ── Webhooks ── */

export interface Webhook {
    id: string;
    url: string;
    events: string[];
    is_active: boolean;
    created_at: string;
}

export function useWebhooks() {
    return useSWR<Webhook[]>("/webhooks", fetcher);
}

/* ── Notification Channels ── */

export interface NotificationChannel {
    id: string;
    name: string;
    type: string;
    config: Record<string, unknown>;
    is_active: boolean;
    created_at: string;
}

export function useNotificationChannels() {
    return useSWR<NotificationChannel[]>("/notifications/channels", fetcher);
}

/* ── API Keys ── */

export interface ApiKey {
    id: string;
    name: string;
    prefix: string;
    scopes: string[];
    created_at: string;
    last_used_at?: string;
    expires_at?: string;
}

export function useApiKeys() {
    return useSWR<ApiKey[]>("/api-keys", fetcher);
}

/* ── Health ── */

export interface HealthStatus {
    status: string;
    version: string;
    services: Record<string, string>;
    timestamp: string;
}

export function useHealth() {
    return useSWR<HealthStatus>("/health", fetcher, { refreshInterval: 30000 });
}

/* ── Tools ── */

export interface ToolInfo {
    name: string;
    version: string;
    category: string;
    description: string;
    capabilities: string[];
    mitre_atlas: string[];
}

export function useTools() {
    return useSWR<ToolInfo[]>("/tools", fetcher);
}
