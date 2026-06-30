"use client";

import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { useSystemHealth } from "@/hooks/useSystemHealth";

export function Header() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll backend health status
  const { data: health, isLoading } = useSystemHealth();

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center space-x-4">
        {/* Placeholder for Breadcrumbs or Active View title */}
        <h2 className="text-sm font-semibold">Terminal</h2>
      </div>
      
      <div className="flex items-center space-x-6">
        {/* Global Time */}
        <div className="flex items-center text-xs text-muted-foreground font-mono">
          <Clock className="mr-2 h-3 w-3" />
          {time}
        </div>

        {/* API Health */}
        <div className="flex items-center text-xs">
          <span className="mr-2 text-muted-foreground">API:</span>
          {isLoading ? (
            <span className="text-yellow-500">Checking...</span>
          ) : health?.status === "ok" ? (
            <span className="text-green-500">Connected</span>
          ) : (
            <span className="text-destructive">Offline</span>
          )}
        </div>
      </div>
    </header>
  );
}
