import type { ApiErrorData } from "~~/app/types/api"
import type { ApiSuccess, CurrentUserData } from "~~/app/types/auth"
import {
  endAuthSession,
  isTerminalAuthError,
} from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError } from "~~/server/utils/django"

export default defineEventHandler(async (event): Promise<
  ApiSuccess<CurrentUserData> | ApiErrorData
> => {
  try {
    return await authenticatedDjangoRequest<ApiSuccess<CurrentUserData>>(
      event,
      "/auth/me/",
    )
  } catch (error) {
    const status = (error as { statusCode?: number }).statusCode
    if (status === 401 || isTerminalAuthError(error)) return endAuthSession(event)
    return proxyDjangoError(event, error)
  }
})
