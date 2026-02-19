"use client";

import React from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface ErrorBoundaryProps {
    children: React.ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

/**
 * React error boundary that catches rendering errors in child components
 * and displays a friendly fallback UI instead of blanking the whole app.
 */
export class ErrorBoundary extends React.Component<
    ErrorBoundaryProps,
    ErrorBoundaryState
> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error("[ErrorBoundary] Caught:", error, info.componentStack);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null });
    };

    handleGoHome = () => {
        this.setState({ hasError: false, error: null });
        window.location.href = "/";
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10">
                        <AlertTriangle className="h-8 w-8 text-destructive" />
                    </div>

                    <div className="space-y-1">
                        <h2 className="text-xl font-bold text-foreground">
                            Something went wrong
                        </h2>
                        <p className="max-w-md text-sm text-muted-foreground">
                            An unexpected error occurred while rendering this page.
                            You can try reloading or return to the dashboard.
                        </p>
                    </div>

                    {this.state.error && (
                        <pre className="max-w-lg overflow-x-auto rounded-lg border border-border bg-secondary/50 px-4 py-2 text-left text-xs text-muted-foreground">
                            {this.state.error.message}
                        </pre>
                    )}

                    <div className="flex gap-3">
                        <button
                            onClick={this.handleRetry}
                            className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-secondary transition-colors"
                        >
                            <RefreshCw className="h-4 w-4" />
                            Try Again
                        </button>
                        <button
                            onClick={this.handleGoHome}
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
                        >
                            <Home className="h-4 w-4" />
                            Go to Dashboard
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
