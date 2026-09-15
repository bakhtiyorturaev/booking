import type { ClubSummary, PaginatedResponse } from "~~/app/types/club"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const input = getQuery(event)
  try {
    return await authenticatedDjangoRequest<PaginatedResponse<ClubSummary>>(
      event,
      "/clubs/",
      { query: { ...input, page_size: 100 } },
    )
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
