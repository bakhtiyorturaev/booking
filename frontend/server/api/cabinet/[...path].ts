import { requestAuthScope, endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  if (requestAuthScope(event) === "customer") throw createError({ statusCode: 403, statusMessage: "Cabinet session required" })
  setResponseHeader(event, "Cache-Control", "private, no-store")
  const path = getRouterParam(event, "path") || ""
  if (!/^[a-zA-Z0-9-]+(?:\/[a-zA-Z0-9-]+)*\/?$/.test(path)) {
    throw createError({ statusCode: 400, statusMessage: "Invalid cabinet path" })
  }
  try {
    const method = event.method
    if (!["GET", "POST", "PATCH", "PUT", "DELETE"].includes(method)) {
      throw createError({ statusCode: 405, statusMessage: "Method not allowed" })
    }
    return await authenticatedDjangoRequest(event, `/cabinet/${path.replace(/\/$/, "")}/`, {
      method,
      query: getQuery(event),
      ...(method !== "GET" ? { body: await readBody(event) } : {}),
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
