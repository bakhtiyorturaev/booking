import type { FetchOptions } from "ofetch"

import {
  getAccessToken,
  getRefreshToken,
  refreshAuthCookies,
} from "~~/server/utils/authCookies"
import { djangoRequest } from "~~/server/utils/django"

type ServerEvent = Parameters<typeof getAccessToken>[0]

const unauthorized = () => {
  const error = new Error("auth.unauthorized") as Error & { statusCode: number }
  error.statusCode = 401
  return error
}

export const authenticatedDjangoRequest = async <T>(
  event: ServerEvent,
  path: string,
  options: FetchOptions = {},
): Promise<T> => {
  let access = getAccessToken(event)
  const hadAccess = Boolean(access)

  if (!access) {
    if (!getRefreshToken(event)) throw unauthorized()
    access = await refreshAuthCookies(event)
  }

  const request = (token: string): Promise<T> => {
    const headers = new Headers(options.headers)
    headers.set("Authorization", `Bearer ${token}`)
    return djangoRequest<T>(event, path, { ...options, headers }) as Promise<T>
  }

  try {
    return await request(access)
  } catch (error) {
    if (!hadAccess || (error as { statusCode?: number }).statusCode !== 401) throw error
    if (!getRefreshToken(event)) throw unauthorized()
    return request(await refreshAuthCookies(event))
  }
}
