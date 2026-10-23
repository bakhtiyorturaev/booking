import { useApiClient } from "~/api/client"
import type {
  BarberAvailability,
  BarberItem,
  BarberProfile,
  BarberStatus,
} from "~/types/barber"
import type { Booking } from "~/types/booking"
import type { PaginatedResponse } from "~/types/club"

export const useBarbersApi = () => {
  const api = useApiClient()

  return {
    getBarbers: (params?: {
      club_id?: string
      branch_id?: string
      search?: string
      query?: string
      city?: string
      ordering?: string
      status?: string
      latitude?: number
      longitude?: number
    }) =>
      api.get<PaginatedResponse<BarberItem>>("/api/barbers", {
        local: true,
        query: params,
      }),

    getBarber: (barberId: string, params?: { latitude?: number; longitude?: number }) =>
      api.get<BarberItem>(`/api/barbers/${encodeURIComponent(barberId)}`, {
        local: true,
        query: params,
      }),

    getAvailability: (barberId: string, date: string) =>
      api.get<BarberAvailability>(`/api/barbers/${encodeURIComponent(barberId)}/availability`, {
        local: true,
        query: { date },
      }),

    bookBarber: (barberId: string, startsAt: string, endsAt?: string) =>
      api.post<Booking>("/api/bookings/barber", {
        local: true,
        body: {
          barber_id: barberId,
          starts_at: startsAt,
          ends_at: endsAt,
        },
      }),

    // Quyidagilar Nuxt BFF orqali ketadi (`local: true`): JWT httpOnly cookie'da
    // turgani uchun brauzerdan to'g'ridan Django'ga yuborilsa 401 keladi.
    getMyProfile: () =>
      api.get<BarberProfile>("/api/barber-profile", { local: true }),

    updateMyProfile: (payload: Partial<BarberProfile>) =>
      api.patch<BarberProfile>("/api/barber-profile", {
        local: true,
        body: payload,
      }),

    updateMyStatus: (status: BarberStatus) =>
      api.post<{ status: BarberStatus; status_display: string; message: string }>("/api/barber-profile/status", {
        local: true,
        body: { status },
      }),

    requestAffiliation: (clubId: string, branchId?: string) =>
      api.post<{ message: string; affiliation_status: string }>("/api/barber-profile/affiliate", {
        local: true,
        body: {
          club_id: clubId,
          branch_id: branchId,
        },
      }),
  }
}
