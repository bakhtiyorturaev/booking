import { useApiClient } from "~/api/client"
import type {
  BarberAvailability,
  BarberItem,
  BarberProfile,
  BarberStatus,
} from "~/types/barber"
import type { Booking } from "~/types/booking"

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
      api.get<BarberItem[]>("/api/barbers", {
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

    getMyProfile: () =>
      api.get<BarberProfile>("/barbers/me/"),

    updateMyProfile: (payload: Partial<BarberProfile>) =>
      api.patch<BarberProfile>("/barbers/me/", {
        body: payload,
      }),

    updateMyStatus: (status: BarberStatus) =>
      api.post<{ status: BarberStatus; status_display: string; message: string }>("/barbers/me/status/", {
        body: { status },
      }),

    requestAffiliation: (clubId: string, branchId?: string) =>
      api.post<{ message: string; affiliation_status: string }>("/barbers/me/affiliate/", {
        body: {
          club_id: clubId,
          branch_id: branchId,
        },
      }),
  }
}
