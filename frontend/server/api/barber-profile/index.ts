import type { ApiErrorData } from "~~/app/types/api"
import type { BarberProfile } from "~~/app/types/barber"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

/**
 * Sartaroshning o'z profili. JWT Nuxt serverdagi httpOnly cookie'da turadi,
 * shuning uchun bu so'rov brauzerdan to'g'ridan Django'ga ketmasligi kerak —
 * aks holda `Authorization` sarlavhasi bo'lmagani uchun doim 401 keladi.
 */
export default defineEventHandler(async (event): Promise<BarberProfile | ApiErrorData> => {
  const method = event.method
  if (!["GET", "PATCH"].includes(method)) {
    throw createError({ statusCode: 405, statusMessage: "Method not allowed" })
  }
  setResponseHeader(event, "Cache-Control", "private, no-store")
  try {
    return await authenticatedDjangoRequest<BarberProfile>(event, "/barbers/me/", {
      method,
      ...(method === "PATCH" ? { body: await readBody(event) } : {}),
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
