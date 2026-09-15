import {
  endAuthSession,
  isTerminalAuthError,
  refreshAuthCookies,
} from "~~/server/utils/authCookies"
import { proxyDjangoError } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    await refreshAuthCookies(event)
    return { success: true }
  } catch (error) {
    if (isTerminalAuthError(error)) return endAuthSession(event)
    return proxyDjangoError(event, error)
  }
})
