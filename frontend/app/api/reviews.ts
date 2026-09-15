import { useApiClient } from "~/api/client"
import type { PaginatedResponse } from "~/types/club"
import type { PublicReview, Review, ReviewPayload } from "~/types/review"

export const useReviewsApi = () => {
  const api = useApiClient()
  return {
    publicList: (clubId: string) =>
      api.get<PaginatedResponse<PublicReview>>(
        `/api/clubs/${encodeURIComponent(clubId)}/reviews`,
        { local: true },
      ),
    mine: () =>
      api.get<PaginatedResponse<Review>>("/api/reviews", { local: true }),
    create: (payload: ReviewPayload) =>
      api.post<Review>("/api/reviews", { local: true, body: payload }),
    update: (id: string, payload: Pick<ReviewPayload, "rating" | "comment">) =>
      api.patch<Review>(`/api/reviews/${encodeURIComponent(id)}`, {
        local: true,
        body: payload,
      }),
    remove: (id: string) =>
      api.delete<unknown>(`/api/reviews/${encodeURIComponent(id)}`, { local: true }),
  }
}
