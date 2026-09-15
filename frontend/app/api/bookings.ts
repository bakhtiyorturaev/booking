import { useApiClient } from "~/api/client"
import type {
  Booking,
  BookingHold,
  BookingHoldPayload,
  BranchAvailability,
} from "~/types/booking"
import type { PaginatedResponse } from "~/types/club"

export const useBookingsApi = () => {
  const api = useApiClient()
  return {
    availability: (branchId: string, date: string, durationMinutes: number) =>
      api.get<BranchAvailability>(
        `/api/branches/${encodeURIComponent(branchId)}/availability`,
        { local: true, query: { date, duration_minutes: durationMinutes } },
      ),
    createHold: (payload: BookingHoldPayload) =>
      api.post<BookingHold>("/api/booking-holds", { local: true, body: payload }),
    create: (holdId: string) =>
      api.post<Booking>("/api/bookings", { local: true, body: { hold_id: holdId } }),
    list: (scope: "all" | "upcoming" | "past" = "all") =>
      api.get<PaginatedResponse<Booking>>("/api/bookings", { local: true, query: { scope } }),
    cancel: (id: string, reason: string) =>
      api.post<Booking>(`/api/bookings/${encodeURIComponent(id)}/cancel`, {
        local: true,
        body: { reason },
      }),
  }
}
