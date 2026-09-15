import type { BranchDetail } from "~~/app/types/club"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id") || ""
  try {
    return await djangoRequest<BranchDetail>(
      event,
      `/branches/${encodeURIComponent(id)}/`,
      { headers: { "Accept-Language": requestLanguage(event) } },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
