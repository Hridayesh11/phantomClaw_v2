"use client";

import { useState } from "react";
import { useLedger } from "@/hooks/useLedger";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Filter } from "lucide-react";

export function TradeTable() {
  const { data, isLoading } = useLedger();
  const [filterSymbol, setFilterSymbol] = useState("");

  const logs = data?.logs || [];
  
  const filteredLogs = filterSymbol 
    ? logs.filter((l: any) => l.symbol.toLowerCase().includes(filterSymbol.toLowerCase()))
    : logs;

  const exportCSV = () => {
    if (!filteredLogs.length) return;
    
    const headers = ["ID", "Timestamp", "Symbol", "Side", "Quantity", "Price", "Fees", "Slippage"];
    const csvContent = [
      headers.join(","),
      ...filteredLogs.map((l: any) => 
        [l.id, l.timestamp, l.symbol, l.side, l.quantity, l.price, l.fees, l.slippage].join(",")
      )
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "phantomclaw_ledger.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Execution Logs</CardTitle>
        <div className="flex space-x-2">
          <div className="relative">
            <Filter className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Filter symbol..."
              className="h-9 w-40 rounded-md border bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              value={filterSymbol}
              onChange={(e) => setFilterSymbol(e.target.value)}
            />
          </div>
          <Button variant="outline" size="sm" onClick={exportCSV} className="h-9">
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground animate-pulse">
            Loading ledger...
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-muted-foreground">
            No execution logs found.
          </div>
        ) : (
          <div className="relative w-full overflow-auto max-h-[600px]">
            <table className="w-full caption-bottom text-sm">
              <thead className="[&_tr]:border-b sticky top-0 bg-card z-10">
                <tr className="border-b transition-colors">
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Time</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Symbol</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Side</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Quantity</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Price</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Fees</th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                {filteredLogs.map((log: any) => (
                  <tr key={log.id} className="border-b transition-colors hover:bg-muted/50">
                    <td className="p-4 align-middle whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="p-4 align-middle font-medium">{log.symbol}</td>
                    <td className={`p-4 align-middle font-bold ${log.side === 'BUY' ? 'text-green-500' : 'text-red-500'}`}>
                      {log.side}
                    </td>
                    <td className="p-4 align-middle text-right">{log.quantity}</td>
                    <td className="p-4 align-middle text-right">${log.price.toFixed(2)}</td>
                    <td className="p-4 align-middle text-right text-muted-foreground">${log.fees.toFixed(2)}</td>
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
