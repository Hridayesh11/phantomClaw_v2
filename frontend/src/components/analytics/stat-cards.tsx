"use client";

import { useLedger } from "@/hooks/useLedger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowUpRight, ArrowDownRight, Target, Activity, Percent } from "lucide-react";

export function StatCards() {
  const { data, isLoading } = useLedger();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-lg border bg-card animate-pulse" />
        ))}
      </div>
    );
  }

  const m = data?.metrics || {};

  const stats = [
    {
      title: "Win Rate",
      value: `${m.win_rate}%`,
      icon: Target,
      trend: m.win_rate >= 50 ? "up" : "down",
    },
    {
      title: "Profit Factor",
      value: m.profit_factor?.toFixed(2),
      icon: Activity,
      trend: m.profit_factor >= 1.5 ? "up" : "down",
    },
    {
      title: "Sharpe Ratio",
      value: m.sharpe_ratio?.toFixed(2),
      icon: Activity,
      trend: m.sharpe_ratio >= 1.0 ? "up" : "down",
    },
    {
      title: "Total Return",
      value: `${m.total_return_pct}%`,
      icon: Percent,
      trend: m.total_return_pct >= 0 ? "up" : "down",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold flex items-center">
                {stat.value}
                {stat.trend === "up" ? (
                  <ArrowUpRight className="ml-2 h-4 w-4 text-green-500" />
                ) : (
                  <ArrowDownRight className="ml-2 h-4 w-4 text-red-500" />
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
