import type { PaginatedResponse } from "~~/app/types/club"
import type { Review } from "~~/app/types/review"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    return await authenticatedDjangoRequest<PaginatedResponse<Review>>(event, "/reviews/", {
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
