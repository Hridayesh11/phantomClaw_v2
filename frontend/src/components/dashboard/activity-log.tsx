"use client";

import { useLedger } from "@/hooks/useLedger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Terminal } from "lucide-react";

export function ActivityLog() {
  const { data, isLoading } = useLedger();

  // For a live activity log, we just take the 10 most recent execution logs
  const logs = data?.logs || [];
  const recentLogs = logs.slice(0, 10); // assuming backend orders by timestamp desc

  return (
    <Card className="col-span-1 lg:col-span-3">
      <CardHeader className="flex flex-row items-center space-y-0 pb-2">
        <Terminal className="h-5 w-5 text-muted-foreground mr-2" />
        <CardTitle className="text-sm font-medium">Live Activity Log</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-32 flex items-center justify-center text-muted-foreground animate-pulse text-xs">
            Connecting to execution stream...
          </div>
        ) : recentLogs.length === 0 ? (
          <div className="h-32 flex items-center justify-center text-muted-foreground text-xs">
            No recent activity.
          </div>
        ) : (
          <div className="space-y-3 mt-2 h-48 overflow-y-auto pr-2">
            {recentLogs.map((log: any) => (
              <div key={log.id} className="flex items-center justify-between text-xs border-b pb-2 last:border-0 last:pb-0">
                <span className="text-muted-foreground font-mono">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className="font-medium text-foreground">
                  {log.symbol}
                </span>
                <span className={`font-bold ${log.side === "BUY" ? "text-green-500" : "text-red-500"}`}>
                  {log.side} {log.quantity}
                </span>
                <span className="text-muted-foreground">
                  @ ${log.price.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
