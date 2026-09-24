import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH"])

// Admin kabineti uchun autentifikatsiyalangan proxy. Barcha /api/cabinet/* chaqiruvlari
// shu yerdan o'tadi: httpOnly cookie'dagi JWT serverda biriktiriladi (401'da avto-refresh)
// va Django'ning /api/v1/cabinet/* endpointlariga uzatiladi.
export default defineEventHandler(async (event) => {
  const rawPath = (getRouterParam(event, "path") || "").replace(/^\/+|\/+$/g, "")
  const method = (event.method || "GET").toUpperCase()
  const query = getQuery(event)
  const body = METHODS_WITH_BODY.has(method)
    ? await readBody(event).catch(() => undefined)
    : undefined

  try {
    return await authenticatedDjangoRequest(event, `/cabinet/${rawPath}/`, {
      method,
      query,
      body,
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
