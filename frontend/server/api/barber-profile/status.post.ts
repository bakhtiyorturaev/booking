import type { ApiErrorData } from "~~/app/types/api"
import type { BarberStatus } from "~~/app/types/barber"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

interface StatusResponse {
  status: BarberStatus
  status_display: string
  message: string
}

export default defineEventHandler(async (event): Promise<StatusResponse | ApiErrorData> => {
  setResponseHeader(event, "Cache-Control", "private, no-store")
  try {
    return await authenticatedDjangoRequest<StatusResponse>(event, "/barbers/me/status/", {
      method: "POST",
      body: await readBody(event),
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
