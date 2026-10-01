import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH"])

// Multipart qism (masalan klub logotipi) kelganda uni qayta FormData'ga yig'ib,
// Django'ga fayl sifatida uzatish uchun. h3 ni o'zi multipart'ni JSON'ga aylantirmaydi.
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

// Admin kabineti uchun autentifikatsiyalangan proxy. Barcha /api/cabinet/* chaqiruvlari
// shu yerdan o'tadi: httpOnly cookie'dagi JWT serverda biriktiriladi (401'da avto-refresh)
// va Django'ning /api/v1/cabinet/* endpointlariga uzatiladi.
export default defineEventHandler(async (event) => {
  const rawPath = (getRouterParam(event, "path") || "").replace(/^\/+|\/+$/g, "")
  const method = (event.method || "GET").toUpperCase()
  const query = getQuery(event)
  const contentType = getRequestHeader(event, "content-type") || ""

  let body: any
  if (METHODS_WITH_BODY.has(method)) {
    body = contentType.startsWith("multipart/form-data")
      ? await readMultipartAsFormData(event).catch(() => undefined)
      : await readBody(event).catch(() => undefined)
  }

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
