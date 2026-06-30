"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Search, TrendingUp, TrendingDown, Activity } from "lucide-react";
import { useMarketData } from "@/hooks/useMarketData";

export function MarketMonitor() {
  const [symbolInput, setSymbolInput] = useState("AAPL");
  const [activeSymbol, setActiveSymbol] = useState("AAPL");

  const { data: market, isLoading, isError, error } = useMarketData(activeSymbol);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbolInput.trim()) {
      setActiveSymbol(symbolInput.trim().toUpperCase());
    }
  };

  return (
    <Card className="col-span-1 lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center space-x-2">
          <Activity className="h-5 w-5 text-primary" />
          <CardTitle>Market Monitor</CardTitle>
        </div>
        <form onSubmit={handleSearch} className="flex space-x-2">
          <input
            type="text"
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            className="h-8 w-32 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="Symbol..."
          />
          <Button type="submit" size="sm" variant="secondary" className="h-8">
            <Search className="h-4 w-4" />
          </Button>
        </form>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-48 flex items-center justify-center text-muted-foreground animate-pulse">
            Fetching live data for {activeSymbol}...
          </div>
        ) : isError ? (
          <div className="h-48 flex items-center justify-center text-destructive text-sm">
            {(error as any)?.response?.data?.detail || "Failed to load market data"}
          </div>
        ) : market ? (
          <div className="space-y-6">
            <div className="flex items-baseline justify-between">
              <div>
                <h2 className="text-3xl font-bold">${market.current_price?.toFixed(2)}</h2>
                <div className="flex items-center text-sm text-muted-foreground space-x-2 mt-1">
                  <span>Vol: {market.volume?.toLocaleString()}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium">OHLC (Today)</div>
                <div className="text-xs text-muted-foreground grid grid-cols-2 gap-x-4 gap-y-1 mt-1">
                  <span>O: {market.open?.toFixed(2)}</span>
                  <span>H: {market.high?.toFixed(2)}</span>
                  <span>L: {market.low?.toFixed(2)}</span>
                  <span>C: {market.close?.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-4 border-t pt-4">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground mb-1">RSI (14)</span>
                <span className={`text-sm font-medium ${market.rsi > 70 ? 'text-red-400' : market.rsi < 30 ? 'text-green-400' : ''}`}>
                  {market.rsi?.toFixed(2) || 'N/A'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground mb-1">MACD</span>
                <span className={`text-sm font-medium ${market.macd > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {market.macd?.toFixed(2) || 'N/A'}
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground mb-1">EMA (20)</span>
                <span className="text-sm font-medium">{market.ema20?.toFixed(2) || 'N/A'}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground mb-1">ATR</span>
                <span className="text-sm font-medium">{market.atr?.toFixed(2) || 'N/A'}</span>
              </div>
            </div>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
