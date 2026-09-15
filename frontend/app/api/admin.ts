import { useApiClient } from "./client"

export const useAdminApi = () => {
  const client = useApiClient()

  return {
    getStats: (language = "uz") =>
      client.get<any>("/api/v1/cabinet/stats/", {
        headers: { "Accept-Language": language },
      }),

    getClubs: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/clubs/", {
        params,
        headers: { "Accept-Language": language },
      }),

    createClub: (payload: any, language = "uz") =>
      client.post<any>("/api/v1/cabinet/clubs/", {
        body: payload,
        headers: { "Accept-Language": language },
      }),

    updateClub: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/v1/cabinet/clubs/${id}/`, {
        body: payload,
        headers: { "Accept-Language": language },
      }),

    deleteClub: (id: string, language = "uz") =>
      client.delete<any>(`/api/v1/cabinet/clubs/${id}/`, {
        headers: { "Accept-Language": language },
      }),

    getBranches: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/branches/", {
        params,
        headers: { "Accept-Language": language },
      }),

    createBranch: (payload: any, language = "uz") =>
      client.post<any>("/api/v1/cabinet/branches/", {
        body: payload,
        headers: { "Accept-Language": language },
      }),

    updateBranch: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/v1/cabinet/branches/${id}/`, {
        body: payload,
        headers: { "Accept-Language": language },
      }),

    deleteBranch: (id: string, language = "uz") =>
      client.delete<any>(`/api/v1/cabinet/branches/${id}/`, {
        headers: { "Accept-Language": language },
      }),

    getZones: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/zones/", {
        params,
        headers: { "Accept-Language": language },
      }),

    createZone: (payload: any, language = "uz") =>
      client.post<any>("/api/v1/cabinet/zones/", {
        body: payload,
        headers: { "Accept-Language": language },
      }),

    updateZone: (id: string, payload: any, language = "uz") =>
      client.patch<any>(`/api/v1/cabinet/zones/${id}/`, {
        body: payload,
        headers: { "Accept-Language": language },
      }),

    deleteZone: (id: string, language = "uz") =>
      client.delete<any>(`/api/v1/cabinet/zones/${id}/`, {
        headers: { "Accept-Language": language },
      }),

    getBookings: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/bookings/", {
        params,
        headers: { "Accept-Language": language },
      }),

    checkInBooking: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/bookings/${id}/check-in/`, {
        headers: { "Accept-Language": language },
      }),

    completeBooking: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/bookings/${id}/complete/`, {
        headers: { "Accept-Language": language },
      }),

    noShowBooking: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/bookings/${id}/no-show/`, {
        headers: { "Accept-Language": language },
      }),

    cancelBooking: (id: string, reason = "", language = "uz") =>
      client.post<any>(`/api/v1/cabinet/bookings/${id}/cancel/`, {
        body: { reason },
        headers: { "Accept-Language": language },
      }),

    getPayments: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/payments/", {
        params,
        headers: { "Accept-Language": language },
      }),

    getPaymentSummary: (language = "uz") =>
      client.get<any>("/api/v1/cabinet/payments/summary/", {
        headers: { "Accept-Language": language },
      }),

    getReviews: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/reviews/", {
        params,
        headers: { "Accept-Language": language },
      }),

    toggleReviewVisibility: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/reviews/${id}/toggle-visibility/`, {
        headers: { "Accept-Language": language },
      }),

    deleteReview: (id: string, language = "uz") =>
      client.delete<any>(`/api/v1/cabinet/reviews/${id}/`, {
        headers: { "Accept-Language": language },
      }),

    getUsers: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/users/", {
        params,
        headers: { "Accept-Language": language },
      }),

    toggleUserStatus: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/users/${id}/toggle-status/`, {
        headers: { "Accept-Language": language },
      }),

    setUserRole: (id: string, role: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/users/${id}/set-role/`, {
        body: { role },
        headers: { "Accept-Language": language },
      }),

    getCities: (language = "uz") =>
      client.get<any>("/api/v1/locations/cities/", {
        headers: { "Accept-Language": language },
      }),

    getDistricts: (cityId?: string, language = "uz") =>
      client.get<any>("/api/v1/locations/districts/", {
        params: cityId ? { city_id: cityId } : undefined,
        headers: { "Accept-Language": language },
      }),

    getBarbers: (params?: Record<string, any>, language = "uz") =>
      client.get<any>("/api/v1/cabinet/barbers/", {
        params,
        headers: { "Accept-Language": language },
      }),

    approveBarberAffiliation: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/barbers/${id}/approve-affiliation/`, {
        headers: { "Accept-Language": language },
      }),

    rejectBarberAffiliation: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/barbers/${id}/reject-affiliation/`, {
        headers: { "Accept-Language": language },
      }),

    toggleBarberStatus: (id: string, language = "uz") =>
      client.post<any>(`/api/v1/cabinet/barbers/${id}/toggle-status/`, {
        headers: { "Accept-Language": language },
      }),
  }
}
