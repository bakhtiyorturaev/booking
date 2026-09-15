import type { BranchListSummary, PaginatedResponse } from "~~/app/types/club"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

const ALLOWED_QUERY_PARAMS = [
  "category",
  "club",
  "city",
  "district",
  "search",
  "min_price_tiyin",
  "max_price_tiyin",
  "min_rating",
  "service_type",
  "latitude",
  "longitude",
  "radius_km",
  "ordering",
]

export default defineEventHandler(async (event) => {
  const input = getQuery(event)
  const query = Object.fromEntries(
    ALLOWED_QUERY_PARAMS
      .filter(key => input[key] !== undefined && input[key] !== "")
      .map(key => [key, String(input[key])]),
  )
  try {
    return await djangoRequest<PaginatedResponse<BranchListSummary>>(
      event,
      "/branches/",
      {
        query: { ...query, page_size: 100 },
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
