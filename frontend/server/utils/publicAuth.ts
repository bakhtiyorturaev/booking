import type { FetchOptions } from "ofetch"
import type { ApiSuccess, AuthResultData, BackendAuthResultData } from "~~/app/types/auth"
import { requestAuthScope, setAuthCookies } from "~~/server/utils/authCookies"
import { djangoRequest, requestLanguage } from "~~/server/utils/django"

type ServerEvent = Parameters<typeof setAuthCookies>[0]

export const completePublicAuth = async (
  event: ServerEvent,
  path: string,
  body: FetchOptions["body"],
): Promise<ApiSuccess<AuthResultData>> => {
  const scope = requestAuthScope(event)
  const expected = path === "/auth/login/" ? (body as { login_type?: string })?.login_type : "customer"
  if (expected !== scope || (path === "/auth/login/" && scope === "customer")) throw createError({ statusCode: 400, statusMessage: "Login scope mismatch" })
  const response = await djangoRequest<ApiSuccess<BackendAuthResultData>>(event, path, {
    method: "POST",
    body,
    headers: { "Accept-Language": requestLanguage(event) },
  }) as ApiSuccess<BackendAuthResultData>
  const { tokens, ...data } = response.data
  setAuthCookies(event, tokens, scope)
  return { ...response, data }
}
