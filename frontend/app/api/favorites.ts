import { useApiClient } from "~/api/client"
import type { FavoriteItem, PaginatedResponse } from "~/types/club"

export const useFavoritesApi = () => {
  const api = useApiClient()
  return {
    list: (query?: Record<string, any>) =>
      api.get<PaginatedResponse<FavoriteItem>>("/api/favorites", { local: true, query }),
    add: (clubId: string) =>
      api.post<FavoriteItem>("/api/favorites", { local: true, body: { club: clubId } }),
    remove: (clubIdOrFavoriteId: string) =>
      api.delete(`/api/favorites/${encodeURIComponent(clubIdOrFavoriteId)}`, { local: true }),
  }
}
