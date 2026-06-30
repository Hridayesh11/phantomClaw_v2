import { MarketMonitor } from "@/components/dashboard/market-monitor";
import { AIRecommendationPanel } from "@/components/trading/ai-panel";
import { ActivityLog } from "@/components/dashboard/activity-log";

export default function Dashboard() {
  return (
    <div className="flex flex-col space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Real-time algorithmic trading overview and execution environment.
        </p>
      </div>

      <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
        <MarketMonitor />
        <AIRecommendationPanel symbol="AAPL" />
        <ActivityLog />
      </div>
      
      {/* Placeholder for Mini positions table */}
    </div>
  );
}
