import type { Booking } from "~~/app/types/booking"
import type { PaginatedResponse } from "~~/app/types/club"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const scope = String(getQuery(event).scope || "all")
  try {
    return await authenticatedDjangoRequest<PaginatedResponse<Booking>>(
      event,
      "/bookings/",
      {
        query: { scope },
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
