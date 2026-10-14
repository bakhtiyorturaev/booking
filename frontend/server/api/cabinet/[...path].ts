import { requestAuthScope, endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

// h3 multipart'ni o'zi JSON'ga aylantirmaydi: fayllarni (klub logotipi/muqovasi) FormData qilib Django'ga uzatamiz.
const readMultipartAsFormData = async (event: Parameters<typeof readMultipartFormData>[0]) => {
  const parts = await readMultipartFormData(event)
  if (!parts) return undefined
  const formData = new FormData()
  for (const part of parts) {
    if (!part.name) continue
    if (part.filename) {
      formData.append(part.name, new Blob([new Uint8Array(part.data)], { type: part.type || "application/octet-stream" }), part.filename)
    } else {
      formData.append(part.name, part.data.toString("utf-8"))
    }
  }
  return formData
}

export default defineEventHandler(async (event) => {
  if (requestAuthScope(event) === "customer") throw createError({ statusCode: 403, statusMessage: "Cabinet session required" })
  setResponseHeader(event, "Cache-Control", "private, no-store")
  const path = getRouterParam(event, "path") || ""
  if (!/^[a-zA-Z0-9-]+(?:\/[a-zA-Z0-9-]+)*\/?$/.test(path)) {
    throw createError({ statusCode: 400, statusMessage: "Invalid cabinet path" })
  }
  const isMultipart = (getRequestHeader(event, "content-type") || "").startsWith("multipart/form-data")
  try {
    const method = event.method
    if (!["GET", "POST", "PATCH", "PUT", "DELETE"].includes(method)) {
      throw createError({ statusCode: 405, statusMessage: "Method not allowed" })
    }
    if (requestAuthScope(event) === "client" && method !== "GET" && !(method === "POST" && /^bookings\/[a-zA-Z0-9-]+\/(confirm|cancel)\/?$/.test(path))) {
      throw createError({ statusCode: 403, statusMessage: "Client kabineti faqat ko‘rish uchun" })
    }
    return await authenticatedDjangoRequest(event, `/cabinet/${path.replace(/\/$/, "")}/`, {
      method,
      query: getQuery(event),
      ...(method !== "GET" ? { body: isMultipart ? await readMultipartAsFormData(event) : await readBody(event) } : {}),
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
