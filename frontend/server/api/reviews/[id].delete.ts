import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  try {
    await authenticatedDjangoRequest<unknown>(event, `/reviews/${encodeURIComponent(id)}/`, {
      method: "DELETE",
      headers: { "Accept-Language": requestLanguage(event) },
    })
    event.node.res.statusCode = 204
    return null
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
