import type { FetchError } from "ofetch"

import type { ApiErrorData } from "~~/app/types/api"
import type { ApiSuccess, AuthTokens } from "~~/app/types/auth"
import { djangoRequest, requestLanguage } from "~~/server/utils/django"

import type { AuthScope } from "~~/shared/authScope"

type ServerEvent = Parameters<typeof getCookie>[0]

export const requestAuthScope = (event: ServerEvent): AuthScope => {
  const scope = getRequestHeader(event, "x-auth-scope") || "customer"
  if (!["customer", "staff", "client"].includes(scope)) throw createError({ statusCode: 400, statusMessage: "Invalid auth scope" })
  return scope as AuthScope
}
const cookieName = (scope: AuthScope, kind: string) => `rezerv_${scope}_${kind}`
const TERMINAL_AUTH_CODES = new Set([
  "auth.user_inactive",
  "auth.user_blocked",
  "auth.user_deleted",
  "auth.refresh_token_missing",
  "auth.session_expired",
  "auth.session_revoked_token_reused",
  "auth.session_id_missing",
])

const cookieOptions = {
  httpOnly: true,
  secure: !import.meta.dev,
  sameSite: "lax" as const,
  path: "/",
}

export const getAccessToken = (event: ServerEvent) => getCookie(event, cookieName(requestAuthScope(event), "access"))
export const getRefreshToken = (event: ServerEvent) => getCookie(event, cookieName(requestAuthScope(event), "refresh"))

export const setAuthCookies = (event: ServerEvent, tokens: AuthTokens, scope = requestAuthScope(event)) => {
  setCookie(event, cookieName(scope, "access"), tokens.access, {
    ...cookieOptions,
    maxAge: 60 * 15,
  })
  setCookie(event, cookieName(scope, "refresh"), tokens.refresh, {
    ...cookieOptions,
    maxAge: 60 * 60 * 24 * 30,
  })
}

export const clearAuthCookies = (event: ServerEvent) => {
  deleteCookie(event, cookieName(requestAuthScope(event), "access"), cookieOptions)
  deleteCookie(event, cookieName(requestAuthScope(event), "refresh"), cookieOptions)
}

export const isTerminalAuthError = (error: unknown) => {
  const data = (error as FetchError<ApiErrorData>).data
  return Boolean(data?.code && TERMINAL_AUTH_CODES.has(data.code))
}

export const endAuthSession = (event: ServerEvent) => {
  clearAuthCookies(event)
  event.node.res.statusCode = 401
  return { success: false as const, code: "auth.unauthorized", message: "auth.unauthorized", errors: null }
}

export const refreshAuthCookies = async (event: ServerEvent) => {
  const refresh = getRefreshToken(event)
  if (!refresh) throw new Error("auth.refresh_token_missing")

  const response = await djangoRequest<ApiSuccess<{ tokens: AuthTokens }>>(
    event,
    "/auth/token/refresh/",
    {
      method: "POST",
      body: { refresh },
      headers: { "Accept-Language": requestLanguage(event) },
    },
  )
  setAuthCookies(event, response.data.tokens)
  return response.data.tokens.access
}
