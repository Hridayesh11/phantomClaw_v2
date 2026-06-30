import { StatCards } from "@/components/analytics/stat-cards";
import { EquityCurve } from "@/components/analytics/equity-curve";
import { TradeTable } from "@/components/ledger/trade-table";

export default function LedgerPage() {
  return (
    <div className="flex flex-col space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Trade Ledger & Analytics</h1>
        <p className="text-muted-foreground">
          Review historical execution logs and portfolio performance metrics.
        </p>
      </div>
      
      <StatCards />
      <EquityCurve />
      <TradeTable />
    </div>
  );
}
