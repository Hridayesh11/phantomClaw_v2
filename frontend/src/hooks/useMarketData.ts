import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/apiClient";

export function useMarketData(symbol: string) {
  return useQuery({
    queryKey: ["market", symbol],
    queryFn: async () => {
      const res = await apiClient.get(`/market/${symbol}`);
      return res.data;
    },
    refetchInterval: 5000,
    retry: false,
    enabled: !!symbol,
  });
}
