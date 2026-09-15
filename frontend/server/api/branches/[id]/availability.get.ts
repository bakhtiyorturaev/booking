import type { BranchAvailability } from "~~/app/types/booking"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  const input = getQuery(event)
  try {
    return await djangoRequest<BranchAvailability>(
      event,
      `/branches/${encodeURIComponent(id)}/availability/`,
      {
        query: {
          date: String(input.date || ""),
          duration_minutes: String(input.duration_minutes || ""),
        },
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
