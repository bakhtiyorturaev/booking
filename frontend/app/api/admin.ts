import { useApiClient } from "./client"

// Admin kabineti API'si. Barcha chaqiruvlar Nuxt server-proxy orqali (`local: true`) ketadi:
//  - /api/cabinet/*   → server/api/cabinet/[...path].ts  (httpOnly cookie'dagi JWT bilan)
//  - /api/locations/* → server/api/locations/[...path].ts (public)
// Shu sabab bu yerda `/api/v1` prefiksi YO'Q — uni Django tomonidagi proxy qo'shadi.
export const useAdminApi = () => {
  const client = useApiClient()

  return {
    getStats: (language = "uz") =>
      client.get<any>("/api/cabinet/stats/", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    // Egalar kabineti dashboard'i — faqat foydalanuvchining o'z muassasalari bo'yicha.
    getOwnerStats: (language = "uz") =>
      client.get<any>("/api/cabinet/owner-stats/", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getClubs: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/clubs/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

    getClub: (id: string, language = "uz") =>
      client.get<any>(`/api/cabinet/clubs/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    createClub: (payload: any, language = "uz") =>
      client.post<any>("/api/cabinet/clubs/", {
        local: true,
        body: payload,
        headers: { "Accept-Language": language },
      }),

    updateClub: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/cabinet/clubs/${id}/`, {
        local: true,
        body: payload,
        headers: { "Accept-Language": language },
      }),

    deleteClub: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/clubs/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getBranches: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/branches/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

    createBranch: (payload: any, language = "uz") =>
      client.post<any>("/api/cabinet/branches/", {
        local: true,
        body: payload,
        headers: { "Accept-Language": language },
      }),

    updateBranch: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/cabinet/branches/${id}/`, {
        local: true,
        body: payload,
        headers: { "Accept-Language": language },
      }),

    deleteBranch: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/branches/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getZones: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/zones/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

    createZone: (payload: any, language = "uz") =>
      client.post<any>("/api/cabinet/zones/", {
        local: true,
        body: payload,
        headers: { "Accept-Language": language },
      }),

    updateZone: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/cabinet/zones/${id}/`, {
        local: true,
        body: payload,
        headers: { "Accept-Language": language },
      }),

    deleteZone: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/zones/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getBookings: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/bookings/", {
        local: true,
        params,
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
        local: true,
        body: { reason },
        headers: { "Accept-Language": language },
      }),

    getPayments: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/payments/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

    getPaymentSummary: (language = "uz") =>
      client.get<any>("/api/cabinet/payments/summary/", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getReviews: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/reviews/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

    toggleReviewVisibility: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/reviews/${id}/toggle-visibility/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    deleteReview: (id: string, language = "uz") =>
      client.delete<any>(`/api/cabinet/reviews/${id}/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getUsers: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/users/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

    toggleUserStatus: (id: string, language = "uz") =>
      client.post<any>(`/api/cabinet/users/${id}/toggle-status/`, {
        local: true,
        headers: { "Accept-Language": language },
      }),

    setUserRole: (id: string, role: string, language = "uz") =>
      client.post<any>(`/api/cabinet/users/${id}/set-role/`, {
        local: true,
        body: { role },
        headers: { "Accept-Language": language },
      }),

    getCities: (language = "uz") =>
      client.get<any>("/api/locations/cities/", {
        local: true,
        headers: { "Accept-Language": language },
      }),

    getDistricts: (cityId?: string, language = "uz") =>
      client.get<any>("/api/locations/districts/", {
        local: true,
        params: cityId ? { city_id: cityId } : undefined,
        headers: { "Accept-Language": language },
      }),

    getBarbers: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/cabinet/barbers/", {
        local: true,
        params,
        headers: { "Accept-Language": language },
      }),

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
