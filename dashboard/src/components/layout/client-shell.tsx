"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { ErrorBoundary } from "./error-boundary";

function LayoutInner({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuth();
    const pathname = usePathname();
    const router = useRouter();
    const isLoginPage = pathname === "/login";

    useEffect(() => {
        if (!isLoading && !isAuthenticated && !isLoginPage) {
            router.replace("/login");
        }
    }, [isLoading, isAuthenticated, isLoginPage, router]);

    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
        );
    }

    // Login page or unauthenticated — bare layout (redirect in progress)
    if (isLoginPage || !isAuthenticated) {
        return <>{children}</>;
    }

    return (
        <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-1 flex-col overflow-hidden">
                <Topbar />
                <main className="flex-1 overflow-y-auto p-6">
                    <ErrorBoundary>{children}</ErrorBoundary>
                </main>
            </div>
        </div>
    );
}

export function ClientShell({ children }: { children: React.ReactNode }) {
    return (
        <AuthProvider>
            <LayoutInner>{children}</LayoutInner>
        </AuthProvider>
    );
}
