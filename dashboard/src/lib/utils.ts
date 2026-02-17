import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/** Relative time formatting (e.g. "3 min ago") */
export function timeAgo(date: string | Date): string {
    const seconds = Math.floor(
        (Date.now() - new Date(date).getTime()) / 1000
    );
    if (seconds < 60) return "just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

/** Capitalize first letter */
export function capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Severity → color mapping */
export function severityColor(severity: string): string {
    const map: Record<string, string> = {
        critical: "text-critical",
        high: "text-high",
        medium: "text-medium",
        low: "text-low",
        info: "text-info",
    };
    return map[severity?.toLowerCase()] ?? "text-muted-foreground";
}

/** Severity → badge class */
export function severityBadge(severity: string): string {
    const map: Record<string, string> = {
        critical: "badge-critical",
        high: "badge-high",
        medium: "badge-medium",
        low: "badge-low",
        info: "badge-info",
    };
    return map[severity?.toLowerCase()] ?? "badge-info";
}

/** Status → badge class */
export function statusColor(status: string): string {
    const map: Record<string, string> = {
        completed: "text-low",
        running: "text-info",
        pending: "text-muted-foreground",
        failed: "text-critical",
        queued: "text-warning",
    };
    return map[status?.toLowerCase()] ?? "text-muted-foreground";
}
