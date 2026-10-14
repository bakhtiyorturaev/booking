import { useApiClient } from "~/api/client"
import type {
  BranchDetail,
  BranchListSummary,
  PaginatedResponse,
} from "~/types/club"

export interface BranchListParams {
  category?: "GAMING_CLUB" | "BARBERSHOP" | "BILLIARDS" | "OTHER"
  service_category?: string
  club?: string
  city?: string
  district?: string
  search?: string
  min_price_tiyin?: number
  max_price_tiyin?: number
  min_rating?: number
  service_type?: string
  latitude?: number
  longitude?: number
  radius_km?: number
  ordering?: string
}

export const useBranchesApi = () => {
  const api = useApiClient()
  return {
    list: (query: BranchListParams = {}) =>
      api.get<PaginatedResponse<BranchListSummary>>("/api/branches", {
        local: true,
        query,
      }),
    top: (query: { service_category?: string; limit?: number } = {}) =>
      api.get<Array<BranchListSummary & { bookings_30d: number }>>("/api/branches/top", {
        local: true,
        query,
      }),
    get: (id: string) =>
      api.get<BranchDetail>(`/api/branches/${encodeURIComponent(id)}`, {
        local: true,
      }),
  }
}
