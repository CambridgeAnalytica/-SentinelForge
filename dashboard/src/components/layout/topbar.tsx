"use client";

import { useAuth } from "@/lib/auth-context";
import { useHealth } from "@/hooks/use-api";
import { LogOut, Activity } from "lucide-react";

export function Topbar() {
    const { user, logout } = useAuth();
    const { data: health } = useHealth();

    return (
        <header className="flex h-14 items-center justify-between border-b border-border bg-card px-6">
            {/* Left: platform info */}
            <div className="flex items-center gap-3">
                <h1 className="text-sm font-semibold text-foreground">
                    SentinelForge
                </h1>
                {health && (
                    <span className="flex items-center gap-1 rounded-full bg-low/15 px-2 py-0.5 text-xs font-medium text-low">
                        <Activity className="h-3 w-3" />
                        v{health.version}
                    </span>
                )}
            </div>

            {/* Right: user & logout */}
            <div className="flex items-center gap-4">
                {user && (
                    <span className="text-xs text-muted-foreground">
                        {user.username}
                        <span className="ml-1 rounded bg-secondary px-1.5 py-0.5 text-[10px] uppercase">
                            {user.role}
                        </span>
                    </span>
                )}
                <button
                    onClick={() => logout()}
                    className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                    title="Logout"
                >
                    <LogOut className="h-4 w-4" />
                </button>
            </div>
        </header>
    );
}
