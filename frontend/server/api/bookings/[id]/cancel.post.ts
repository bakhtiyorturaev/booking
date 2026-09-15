import type { Booking } from "~~/app/types/booking"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  try {
    return await authenticatedDjangoRequest<Booking>(
      event,
      `/bookings/${encodeURIComponent(id)}/cancel/`,
      {
        method: "POST",
        body: await readBody<{ reason?: string }>(event),
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
