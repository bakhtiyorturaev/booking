import type { ApiErrorData } from "~~/app/types/api"
import type {
  ApiSuccess,
  CurrentUserData,
  ProfileUpdatePayload,
} from "~~/app/types/auth"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event): Promise<
  ApiSuccess<CurrentUserData> | ApiErrorData
> => {
  try {
    return await authenticatedDjangoRequest<ApiSuccess<CurrentUserData>>(
      event,
      "/auth/me/",
      {
        method: "PATCH",
        body: await readBody<ProfileUpdatePayload>(event),
        headers: { "Accept-Language": requestLanguage(event) },
      },
    )
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
