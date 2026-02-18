"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
    LayoutDashboard,
    Search,
    TrendingDown,
    Calendar,
    ShieldCheck,
    FileText,
    Bell,
    Key,
    Settings,
    ChevronLeft,
    Shield,
    ClipboardList,
    Swords,
} from "lucide-react";
import { useState } from "react";

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/findings", label: "Findings", icon: Search },
    { href: "/drift", label: "Drift", icon: TrendingDown },
    { href: "/schedules", label: "Schedules", icon: Calendar },
    { href: "/compliance", label: "Compliance", icon: ShieldCheck },
    { href: "/reports", label: "Reports", icon: FileText },
    { href: "/scenarios", label: "Scenarios", icon: Swords },
    { href: "/audit", label: "Audit Log", icon: ClipboardList },
    { type: "divider" as const },
    { href: "/settings/notifications", label: "Notifications", icon: Bell },
    { href: "/settings/api-keys", label: "API Keys", icon: Key },
    { href: "/settings/webhooks", label: "Webhooks", icon: Settings },
] as const;

export function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    return (
        <aside
            className={cn(
                "flex flex-col border-r border-sidebar-border bg-sidebar-background transition-all duration-200",
                collapsed ? "w-16" : "w-56"
            )}
        >
            {/* Logo */}
            <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
                <Shield className="h-6 w-6 shrink-0 text-primary" />
                {!collapsed && (
                    <span className="text-sm font-bold tracking-tight text-sidebar-foreground">
                        SentinelForge
                    </span>
                )}
            </div>

            {/* Nav */}
            <nav className="flex-1 space-y-1 px-2 py-3 overflow-y-auto">
                {navItems.map((item, i) => {
                    if ("type" in item && item.type === "divider") {
                        return <div key={i} className="my-2 border-t border-sidebar-border" />;
                    }
                    const navItem = item as { href: string; label: string; icon: React.ComponentType<{ className?: string }> };
                    const active = pathname === navItem.href;
                    const Icon = navItem.icon;
                    return (
                        <Link
                            key={navItem.href}
                            href={navItem.href}
                            className={cn(
                                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                                active
                                    ? "bg-sidebar-accent text-sidebar-primary"
                                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                            )}
                        >
                            <Icon className="h-4 w-4 shrink-0" />
                            {!collapsed && <span>{navItem.label}</span>}
                        </Link>
                    );
                })}
            </nav>

            {/* Collapse toggle */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="flex h-10 items-center justify-center border-t border-sidebar-border text-sidebar-foreground/50 hover:text-sidebar-foreground transition-colors"
            >
                <ChevronLeft
                    className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")}
                />
            </button>
        </aside>
    );
}
