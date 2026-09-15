import type { BarberAvailability } from "~~/app/types/barber"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id")
  const input = getQuery(event)
  try {
    return await djangoRequest<BarberAvailability>(
      event,
      `/barbers/${encodeURIComponent(String(id))}/availability/`,
      {
        query: { date: input.date ? String(input.date) : undefined },
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
