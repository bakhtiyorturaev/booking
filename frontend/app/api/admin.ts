import { useApiClient } from "./client"
import type { BillingVenue, ManualVenuePayment, ManualPaymentInput, BillingSummary, Paginated } from "~/types/venueBilling"

export const useAdminApi = () => {
  const client = useApiClient()

  return {
    getStats: (language = "uz") =>
      client.get<any>("/api/cabinet/stats/", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getServiceTypes: () => client.get<{ id: string; code: string; name: string }[]>("/api/cabinet/service-types/", { local: true }),

    getClubs: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/clubs/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    createClub: (payload: any, language = "uz") =>
      client.post<any>("/api/cabinet/clubs/", {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    updateClub: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/cabinet/clubs/${id}/`, {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    deleteClub: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/clubs/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getBranches: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/branches/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    createBranch: (payload: any, language = "uz") =>
      client.post<any>("/api/cabinet/branches/", {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    updateBranch: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/cabinet/branches/${id}/`, {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    deleteBranch: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/branches/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getZones: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/zones/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    createZone: (payload: any, language = "uz") =>
      client.post<any>("/api/cabinet/zones/", {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    updateZone: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/cabinet/zones/${id}/`, {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    deleteZone: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/zones/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    createBooking: (body: Record<string, unknown>) => client.post<any>("/api/cabinet/bookings/", { local: true, body }),
    createBarber: (body: Record<string, unknown>) => client.post<any>("/api/cabinet/barbers/", { local: true, body }),

    getBookings: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/bookings/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    checkInBooking: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/bookings/${id}/check-in/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    completeBooking: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/bookings/${id}/complete/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    noShowBooking: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/bookings/${id}/no-show/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    cancelBooking: (id: string, reason = "", language = "uz") =>
      client.post<any>(`/api/cabinet/bookings/${id}/cancel/`, {
        body: { reason },
        local: true,
        headers: { "Accept-Language": language },
      }),

    getPayments: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/payments/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    getPaymentSummary: (language = "uz") =>
      client.get<any>("/api/cabinet/payments/summary/", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getBranchBilling: (query?: Record<string, string | number>) => client.get<Paginated<BillingVenue>>("/api/cabinet/branch-billing/", { local: true, query }),
    setFreeMode: (kind: "branch" | "barber", id: string, isFree: boolean) => client.post<BillingVenue>(`/api/cabinet/${kind}-billing/${encodeURIComponent(id)}/free-mode/`, { local: true, body: { is_free: isFree } }),
    getBarberBilling: (params?: Record<string, string | number>) => client.get<Paginated<BillingVenue>>("/api/cabinet/barber-billing/", { local: true, params }),
    getVenueBilling: (params?: Record<string, string | number>) =>
      client.get<Paginated<BillingVenue>>("/api/cabinet/venue-billing/", { local: true, params }),
    getVenuePayments: (params?: Record<string, string | number>) =>
      client.get<Paginated<ManualVenuePayment>>("/api/cabinet/venue-payments/", { local: true, params }),
    recordVenuePayment: (body: ManualPaymentInput) =>
      client.post<ManualVenuePayment>("/api/cabinet/venue-payments/", { local: true, body }),
    getVenuePaymentSummary: () =>
      client.get<BillingSummary>("/api/cabinet/venue-payments/summary/", { local: true }),

    getUsers: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/users/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    toggleUserStatus: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/users/${id}/toggle-status/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    setUserRole: (id: string, role: string, language = "uz") =>
      client.post<any>(`/api/cabinet/users/${id}/set-role/`, {
        body: { role },
        local: true,
        headers: { "Accept-Language": language },
      }),

    createUser: (payload: { username: string; phone: string; full_name: string; password: string }, language = "uz") =>
      client.post<any>("/api/cabinet/users/", {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    setUserPassword: (id: string, payload: { new_password: string; confirm_password: string }, language = "uz") =>
      client.post<any>(`/api/cabinet/users/${id}/set-password/`, {
        body: payload,
        local: true,
        headers: { "Accept-Language": language },
      }),

    getCities: (language = "uz") =>
      client.get<any>("/api/locations/cities", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getDistricts: (cityId?: string, language = "uz") =>
      client.get<any>("/api/locations/districts", {
        local: true,
        params: cityId ? { city_id: cityId } : undefined,
        headers: { "Accept-Language": language },
      }),

    getBarbers: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/barbers/", {
        params,
        local: true,
        headers: { "Accept-Language": language },
      }),

    updateBarber: (id: string, body: { full_name: string; phone: string; status: string; work_start_time: string; work_end_time: string; working_days: number[] }) =>
      client.patch(`/api/cabinet/barbers/${encodeURIComponent(id)}/`, { local: true, body }),

    approveBarberAffiliation: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/barbers/${id}/approve-affiliation/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    rejectBarberAffiliation: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/barbers/${id}/reject-affiliation/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    toggleBarberStatus: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/barbers/${id}/toggle-status/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),
  }
}
