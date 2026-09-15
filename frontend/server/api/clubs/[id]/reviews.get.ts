import type { PaginatedResponse } from "~~/app/types/club"
import type { PublicReview } from "~~/app/types/review"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  try {
    return await djangoRequest<PaginatedResponse<PublicReview>>(
      event,
      `/clubs/${encodeURIComponent(id)}/reviews/`,
      { headers: { "Accept-Language": requestLanguage(event) } },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
