"use client";

import { useState } from "react";
import { useAttackRuns } from "@/hooks/use-api";
import { cn, severityBadge, statusColor, timeAgo, capitalize } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { NewScanModal } from "@/components/new-scan-modal";
import {
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Plus,
  Shield,
} from "lucide-react";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
  info: "#0ea5e9",
};

export default function DashboardPage() {
  const router = useRouter();
  const { data: runs, isLoading } = useAttackRuns();
  const [showNewScan, setShowNewScan] = useState(false);

  if (isLoading) {
    return <PageSkeleton />;
  }

  const allRuns = runs ?? [];
  const allFindings = allRuns.flatMap((r) => r.findings ?? []);
  const activeRuns = allRuns.filter((r) => r.status === "running").length;
  const criticalCount = allFindings.filter(
    (f) => f.severity === "critical"
  ).length;
  const passRate =
    allRuns.length > 0
      ? Math.round(
        (allRuns.filter((r) => (r.findings?.length ?? 0) === 0).length /
          allRuns.length) *
        100
      )
      : 100;

  // Severity breakdown for donut
  const severityCounts = Object.entries(
    allFindings.reduce<Record<string, number>>((acc, f) => {
      const s = f.severity?.toLowerCase() ?? "info";
      acc[s] = (acc[s] ?? 0) + 1;
      return acc;
    }, {})
  ).map(([name, value]) => ({ name: capitalize(name), value }));

  // Trend data: findings per day (last 14 days)
  const trendData = buildTrend(allFindings);

  const stats = [
    {
      label: "Total Scans",
      value: allRuns.length,
      icon: Shield,
      color: "text-primary",
    },
    {
      label: "Active",
      value: activeRuns,
      icon: Activity,
      color: "text-info",
    },
    {
      label: "Critical Findings",
      value: criticalCount,
      icon: AlertTriangle,
      color: "text-critical",
    },
    {
      label: "Pass Rate",
      value: `${passRate}%`,
      icon: CheckCircle2,
      color: "text-low",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Scan Dashboard</h2>
          <p className="text-sm text-muted-foreground">
            Overview of attack runs, findings, and security posture
          </p>
        </div>
        <button
          onClick={() => setShowNewScan(true)}
          className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" /> New Scan
        </button>
      </div>

      {showNewScan && <NewScanModal onClose={() => setShowNewScan(false)} />}

      {/* Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-border bg-card p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                {s.label}
              </span>
              <s.icon className={cn("h-4 w-4", s.color)} />
            </div>
            <p className="mt-2 text-2xl font-bold text-foreground">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Severity donut */}
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            Severity Breakdown
          </h3>
          <div className="h-52">
            {severityCounts.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityCounts}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {severityCounts.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={
                          SEVERITY_COLORS[entry.name.toLowerCase()] ?? "#64748b"
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "hsl(224 71% 4%)",
                      border: "1px solid hsl(215 27% 16%)",
                      borderRadius: "0.5rem",
                      color: "#fff",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState text="No findings yet" />
            )}
          </div>
          {/* Legend */}
          <div className="mt-2 flex flex-wrap gap-3">
            {severityCounts.map((s) => (
              <span
                key={s.name}
                className="flex items-center gap-1 text-xs text-muted-foreground"
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{
                    background:
                      SEVERITY_COLORS[s.name.toLowerCase()] ?? "#64748b",
                  }}
                />
                {s.name} ({s.value})
              </span>
            ))}
          </div>
        </div>

        {/* Trend chart */}
        <div className="rounded-xl border border-border bg-card p-4 lg:col-span-2">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            Findings Trend (14d)
          </h3>
          <div className="h-52">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="gradFill" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="0%"
                        stopColor="#22c55e"
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="100%"
                        stopColor="#22c55e"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "#94a3b8" }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(224 71% 4%)",
                      border: "1px solid hsl(215 27% 16%)",
                      borderRadius: "0.5rem",
                      color: "#fff",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#22c55e"
                    fill="url(#gradFill)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState text="No trend data yet" />
            )}
          </div>
        </div>
      </div>

      {/* Recent scans table */}
      <div className="rounded-xl border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold text-foreground">
            Recent Scans
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-2 font-medium">Scenario</th>
                <th className="px-4 py-2 font-medium">Target</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Findings</th>
                <th className="px-4 py-2 font-medium">Started</th>
              </tr>
            </thead>
            <tbody>
              {allRuns.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-muted-foreground"
                  >
                    No scans yet. Run your first attack to see results here.
                  </td>
                </tr>
              ) : (
                allRuns.slice(0, 20).map((run) => (
                  <tr
                    key={run.id}
                    onClick={() => router.push(`/attacks/${run.id}`)}
                    className="border-b border-border last:border-0 hover:bg-secondary/50 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-2.5 font-medium text-foreground">
                      {run.scenario_id}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">
                      {run.target_model}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
                          statusColor(run.status)
                        )}
                      >
                        {run.status === "running" && (
                          <Clock className="h-3 w-3 animate-spin" />
                        )}
                        {capitalize(run.status)}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <FindingsBadges findings={run.findings ?? []} />
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {run.started_at ? timeAgo(run.started_at) : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ── Helpers ── */

function FindingsBadges({ findings }: { findings: { severity: string }[] }) {
  if (findings.length === 0)
    return <span className="text-xs text-muted-foreground">—</span>;

  const counts = findings.reduce<Record<string, number>>((acc, f) => {
    const s = f.severity?.toLowerCase() ?? "info";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex gap-1">
      {Object.entries(counts).map(([sev, count]) => (
        <span
          key={sev}
          className={cn(
            "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
            severityBadge(sev)
          )}
        >
          {count}
        </span>
      ))}
    </div>
  );
}

function buildTrend(findings: { created_at: string }[]) {
  const days = 14;
  const now = new Date();
  const buckets: Record<string, number> = {};

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(5, 10); // MM-DD
    buckets[key] = 0;
  }

  for (const f of findings) {
    const key = new Date(f.created_at).toISOString().slice(5, 10);
    if (key in buckets) buckets[key]++;
  }

  return Object.entries(buckets).map(([date, count]) => ({ date, count }));
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
      {text}
    </div>
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-secondary" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-xl bg-secondary"
          />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-xl bg-secondary" />
    </div>
  );
}
