import type { ApiSuccess, BackendAuthResultData } from "~~/app/types/auth"
import { setAuthCookies } from "~~/server/utils/authCookies"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

interface WebLoginCheckBackendResponse {
  status: "PENDING" | "SUCCESS" | "BLOCKED"
  user?: BackendAuthResultData["user"]
  tokens?: BackendAuthResultData["tokens"]
  is_new_user?: boolean
}

export default defineEventHandler(async (event) => {
  try {
    const query = getQuery(event)
    const token = String(query.token || "")
    if (!token) {
      throw createError({ statusCode: 400, message: "Token is required" })
    }

    const response = (await djangoRequest<ApiSuccess<WebLoginCheckBackendResponse>>(
      event,
      `/auth/telegram-web/check/${encodeURIComponent(token)}/`,
      {
        method: "GET",
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )) as ApiSuccess<WebLoginCheckBackendResponse>

    if (response.data?.status === "SUCCESS" && response.data.tokens) {
      setAuthCookies(event, response.data.tokens)
      const { tokens, ...restData } = response.data
      return {
        ...response,
        data: restData,
      }
    }

    return response
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
