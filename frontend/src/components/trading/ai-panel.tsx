"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BrainCircuit, Loader2, PlayCircle } from "lucide-react";
import { useAIPipeline } from "@/hooks/useAIPipeline";

export function AIRecommendationPanel({ symbol = "AAPL" }: { symbol?: string }) {
  const { runAnalysis, analyzing, result, error } = useAIPipeline();

  const handleAnalyze = () => {
    runAnalysis(symbol);
  };

  return (
    <Card className="col-span-1 flex flex-col">
      <CardHeader className="pb-3 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BrainCircuit className="h-5 w-5 text-primary" />
            <CardTitle>AI Pipeline</CardTitle>
          </div>
          <Button 
            size="sm" 
            onClick={handleAnalyze} 
            disabled={analyzing}
            className="h-8"
          >
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <PlayCircle className="h-4 w-4 mr-2" />}
            {analyzing ? "Running..." : "Run Analysis"}
          </Button>
        </div>
        <CardDescription>
          Multi-agent evaluation for {symbol}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="flex-1 p-0 flex flex-col">
        {!analyzing && !result && !error && (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground p-6">
            Click &quot;Run Analysis&quot; to trigger the multi-agent pipeline.
          </div>
        )}

        {analyzing && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-4">
            <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-muted-foreground animate-pulse">Running consensus engines...</span>
          </div>
        )}

        {error && (
          <div className="flex-1 flex items-center justify-center p-6 text-sm text-destructive text-center">
            {error}
          </div>
        )}

        {result && (
          <div className="p-4 space-y-4 overflow-y-auto">
            {/* Final Decision */}
            <div className="rounded-lg border bg-muted/30 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Final Decision</span>
                <span className={`text-sm font-bold px-2 py-1 rounded-md ${
                  result.execution_decision.decision === "EXECUTE" ? "bg-green-500/20 text-green-500" :
                  result.execution_decision.decision === "REVIEW_REQUIRED" ? "bg-yellow-500/20 text-yellow-500" :
                  "bg-red-500/20 text-red-500"
                }`}>
                  {result.execution_decision.decision}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                Action: <strong className="text-foreground">{result.trade_recommendation.action}</strong> 
                {" "}({result.trade_recommendation.quantity} shares)
              </p>
            </div>

            {/* Gauges Placeholder */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg border p-3 flex flex-col items-center justify-center">
                <span className="text-xs text-muted-foreground mb-1">ArmorIQ Risk</span>
                <span className="text-xl font-bold">{result.risk_assessment.risk_score} / 100</span>
                <span className="text-xs text-muted-foreground mt-1 capitalize">{result.risk_assessment.risk_level.toLowerCase()}</span>
              </div>
              <div className="rounded-lg border p-3 flex flex-col items-center justify-center">
                <span className="text-xs text-muted-foreground mb-1">Trust Score</span>
                <span className="text-xl font-bold">{result.trust_assessment.trust_score}%</span>
                <span className="text-xs text-muted-foreground mt-1 capitalize">{result.trust_assessment.trust_level.toLowerCase()}</span>
              </div>
            </div>

            {/* Reasoning summary */}
            <div className="text-sm">
              <h4 className="font-semibold mb-1">Primary Rationale</h4>
              <p className="text-muted-foreground leading-relaxed">
                {result.trade_recommendation.reason}
              </p>
            </div>
            
            <div className="text-sm border-t pt-2">
              <h4 className="font-semibold mb-1 text-red-400">Challenge Agent (Dissent)</h4>
              <p className="text-muted-foreground leading-relaxed">
                {result.challenge_result.opposing_reasoning}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
