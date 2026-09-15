import type { Review, ReviewPayload } from "~~/app/types/review"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  try {
    return await authenticatedDjangoRequest<Review>(
      event,
      `/reviews/${encodeURIComponent(id)}/`,
      {
        method: "PATCH",
        body: await readBody<Pick<ReviewPayload, "rating" | "comment">>(event),
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
