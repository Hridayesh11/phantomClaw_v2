import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/apiClient";

export function useSystemHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await apiClient.get("/health");
      return res.data;
    },
    refetchInterval: 30000,
  });
}
