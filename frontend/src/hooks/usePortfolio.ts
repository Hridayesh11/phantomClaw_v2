import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/apiClient";

export function usePortfolio() {
  return useQuery({
    queryKey: ["portfolio"],
    queryFn: async () => {
      const res = await apiClient.get("/portfolio");
      return res.data;
    },
    refetchInterval: 10000,
  });
}
