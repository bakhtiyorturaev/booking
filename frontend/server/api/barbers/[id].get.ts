import type { BarberItem } from "~~/app/types/barber"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  const input = getQuery(event)
  try {
    return await djangoRequest<BarberItem>(
      event,
      `/barbers/${encodeURIComponent(id)}/`,
      {
        query: {
          latitude: input.latitude ? String(input.latitude) : undefined,
          longitude: input.longitude ? String(input.longitude) : undefined,
        },
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
