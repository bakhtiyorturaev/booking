import type { ClubSummary } from "~~/app/types/club"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const slug = getRouterParam(event, "slug") || ""
  try {
    return await authenticatedDjangoRequest<ClubSummary>(
      event,
      `/clubs/${encodeURIComponent(slug)}/`,
    )
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
