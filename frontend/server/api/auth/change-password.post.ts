import type { ApiSuccess, BackendAuthResultData } from "~~/app/types/auth"
import { setAuthCookies } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const response = await authenticatedDjangoRequest<ApiSuccess<BackendAuthResultData>>(
      event,
      "/auth/password/change/",
      {
        method: "POST",
        body,
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )

    if (response?.data?.tokens) {
      setAuthCookies(event, response.data.tokens)
    }

    const { tokens, ...data } = response.data
    return { ...response, data }
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
