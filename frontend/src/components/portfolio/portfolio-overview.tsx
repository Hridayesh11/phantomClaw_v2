"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DollarSign, Percent, TrendingUp } from "lucide-react";
import { usePortfolio } from "@/hooks/usePortfolio";

export function PortfolioOverview() {
  const { data: portfolio, isLoading } = usePortfolio();

  if (isLoading) {
    return <div className="h-32 rounded-lg border bg-card animate-pulse" />;
  }

  const cash = portfolio?.cash || 0;
  const initial = portfolio?.initial_cash || 100000;
  
  // Note: True equity would require live prices for open positions.
  // For this widget, we show cash balance and realized PnL proxy.
  
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Available Cash</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">${cash.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          <p className="text-xs text-muted-foreground">
            Buying power
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{portfolio?.positions?.length || 0}</div>
          <p className="text-xs text-muted-foreground">
            Currently held assets
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Initial Margin</CardTitle>
          <Percent className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">${initial.toLocaleString()}</div>
          <p className="text-xs text-muted-foreground">
            Starting paper balance
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
