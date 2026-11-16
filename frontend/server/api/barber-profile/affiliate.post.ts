import type { ApiErrorData } from "~~/app/types/api"
import type { AffiliationStatus } from "~~/app/types/barber"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

interface AffiliateResponse {
  affiliation_status: AffiliationStatus
  message: string
}

export default defineEventHandler(async (event): Promise<AffiliateResponse | ApiErrorData> => {
  setResponseHeader(event, "Cache-Control", "private, no-store")
  try {
    return await authenticatedDjangoRequest<AffiliateResponse>(
      event,
      "/barbers/me/affiliate/",
      {
        method: "POST",
        body: await readBody(event),
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
