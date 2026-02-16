"use client";

import { useWebhooks } from "@/hooks/use-api";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function WebhooksPage() {
    const router = useRouter();

    // Redirect to notifications page which includes webhooks
    useEffect(() => {
        router.replace("/settings/notifications");
    }, [router]);

    return null;
}
