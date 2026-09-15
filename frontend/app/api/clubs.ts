import { useApiClient } from "~/api/client"
import type { ClubSummary, PaginatedResponse } from "~/types/club"

export const useClubsApi = () => {
  const api = useApiClient()
  return {
    list: (query?: Record<string, any>) =>
      api.get<PaginatedResponse<ClubSummary>>("/api/clubs", { local: true, query }),
    get: (slug: string) => api.get<ClubSummary>(`/api/clubs/${encodeURIComponent(slug)}`, {
      local: true,
    }),
  }
}
