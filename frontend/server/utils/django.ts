import type { FetchError, FetchOptions } from "ofetch"

import type { ApiErrorData } from "~~/app/types/api"

type ServerEvent = Parameters<typeof getRequestHeader>[0]

const isApiError = (value: unknown): value is ApiErrorData => {
  if (!value || typeof value !== "object") return false
  const data = value as Partial<ApiErrorData>
  return data.success === false
    && typeof data.code === "string"
    && typeof data.message === "string"
}

export const requestLanguage = (event: ServerEvent) =>
  getRequestHeader(event, "accept-language") || "uz"

export const otpProtectionHeaders = (event: ServerEvent) => {
  const existingDeviceId = getCookie(event, "otp_device")
  const deviceId = existingDeviceId || globalThis.crypto.randomUUID()
  if (!existingDeviceId) {
    setCookie(event, "otp_device", deviceId, {
      httpOnly: true,
      sameSite: "lax",
      secure: getRequestProtocol(event) === "https",
      maxAge: 365 * 24 * 60 * 60,
      path: "/",
    })
  }
  return {
    "Accept-Language": requestLanguage(event),
    "X-Device-ID": deviceId,
    "X-Forwarded-For": getRequestIP(event, { xForwardedFor: true }) || "",
  }
}

export const djangoRequest = <T>(
  event: ServerEvent,
  path: string,
  options: FetchOptions = {},
) => {
  const config = useRuntimeConfig()
  return $fetch<T>(path, {
    baseURL: config.djangoApiBaseUrl,
    ...options,
  })
}

export const proxyDjangoError = (event: ServerEvent, error: unknown) => {
  const fetchError = error as FetchError<ApiErrorData>
  const data = isApiError(fetchError.data)
    ? fetchError.data
    : { success: false as const, code: "common.backend_unavailable", message: "common.backend_unavailable", errors: null }

  event.node.res.statusCode = fetchError.statusCode || 502
  return data
}
