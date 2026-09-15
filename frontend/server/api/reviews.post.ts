import type { Review, ReviewPayload } from "~~/app/types/review"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    return await authenticatedDjangoRequest<Review>(event, "/reviews/", {
      method: "POST",
      body: await readBody<ReviewPayload>(event),
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
