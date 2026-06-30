"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { usePortfolio } from "@/hooks/usePortfolio";

export function ActivePositions() {
  const { data: portfolio, isLoading } = usePortfolio();

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Open Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            <div className="h-10 w-full animate-pulse bg-muted rounded" />
            <div className="h-10 w-full animate-pulse bg-muted rounded" />
          </div>
        ) : !portfolio?.positions || portfolio.positions.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground">
            No active positions.
          </div>
        ) : (
          <div className="relative w-full overflow-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                  <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Symbol</th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Quantity</th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Avg Entry</th>
                  <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Realized PnL</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {portfolio.positions.map((pos: any) => (
                  <tr key={pos.symbol} className="border-b transition-colors hover:bg-muted/50">
                    <td className="p-4 align-middle font-medium">{pos.symbol}</td>
                    <td className="p-4 align-middle text-right">{pos.quantity}</td>
                    <td className="p-4 align-middle text-right">${pos.average_entry_price.toFixed(2)}</td>
                    <td className={`p-4 align-middle text-right ${pos.realized_pnl > 0 ? "text-green-500" : pos.realized_pnl < 0 ? "text-red-500" : ""}`}>
                      ${pos.realized_pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
