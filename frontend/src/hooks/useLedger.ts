import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/services/apiClient";

export function useLedger() {
  return useQuery({
    queryKey: ["ledger"],
    queryFn: async () => {
      const res = await apiClient.get("/ledger");
      return res.data;
    },
    refetchInterval: 30000,
  });
}
