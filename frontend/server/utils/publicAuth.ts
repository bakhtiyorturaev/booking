import type { FetchOptions } from "ofetch"
import type { ApiSuccess, AuthResultData, BackendAuthResultData } from "~~/app/types/auth"
import { setAuthCookies } from "~~/server/utils/authCookies"
import { djangoRequest, requestLanguage } from "~~/server/utils/django"

type ServerEvent = Parameters<typeof setAuthCookies>[0]

export const completePublicAuth = async (
  event: ServerEvent,
  path: string,
  body: FetchOptions["body"],
): Promise<ApiSuccess<AuthResultData>> => {
  const response = await djangoRequest<ApiSuccess<BackendAuthResultData>>(event, path, {
    method: "POST",
    body,
    headers: { "Accept-Language": requestLanguage(event) },
  }) as ApiSuccess<BackendAuthResultData>
  const { tokens, ...data } = response.data
  setAuthCookies(event, tokens)
  return { ...response, data }
}
