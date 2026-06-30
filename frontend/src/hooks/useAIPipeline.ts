import { useState } from "react";
import { apiClient } from "@/services/apiClient";

export function useAIPipeline() {
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async (symbol: string) => {
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiClient.post(`/analyze/${symbol}`);
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  return { runAnalysis, analyzing, result, error };
}
