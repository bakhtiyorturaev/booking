import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

// Shaharlar/tumanlar public (AllowAny) — autentifikatsiya shart emas.
// /api/locations/* → Django /api/v1/locations/* ga uzatadi.
export default defineEventHandler(async (event) => {
  const rawPath = (getRouterParam(event, "path") || "").replace(/^\/+|\/+$/g, "")

  try {
    return await djangoRequest<unknown>(event, `/locations/${rawPath}/`, {
      method: "GET",
      query: getQuery(event),
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
