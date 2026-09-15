import type { BarberItem } from "~~/app/types/barber"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

const ALLOWED_QUERY_PARAMS = [
  "club_id",
  "branch_id",
  "search",
  "query",
  "city",
  "status",
  "ordering",
  "latitude",
  "longitude",
]

export default defineEventHandler(async (event) => {
  const input = getQuery(event)
  const query = Object.fromEntries(
    ALLOWED_QUERY_PARAMS
      .filter(key => input[key] !== undefined && input[key] !== "")
      .map(key => [key, String(input[key])]),
  )
  try {
    return await djangoRequest<BarberItem[]>(
      event,
      "/barbers/",
      {
        query,
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
