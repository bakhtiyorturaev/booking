import type { BranchListSummary } from "~~/app/types/club"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const input = getQuery(event)
  const query = Object.fromEntries(
    ["service_category", "limit"]
      .filter(key => input[key] !== undefined && input[key] !== "")
      .map(key => [key, String(input[key])]),
  )
  try {
    return await djangoRequest<Array<BranchListSummary & { bookings_30d: number }>>(
      event,
      "/branches/top/",
      {
        query,
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
