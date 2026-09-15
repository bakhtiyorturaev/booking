import type { Payment } from "~~/app/types/subscription"
import { endAuthSession, isTerminalAuthError } from "~~/server/utils/authCookies"
import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    const headers = new Headers({ "Accept-Language": requestLanguage(event) })
    const idempotencyKey = getHeader(event, "Idempotency-Key")
    if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey)
    return await authenticatedDjangoRequest<Payment>(event, "/payments/checkout/", {
      method: "POST",
      headers,
      body: await readBody<{ plan_code: string }>(event),
    })
  } catch (error) {
    if ((error as { statusCode?: number }).statusCode === 401 || isTerminalAuthError(error)) {
      return endAuthSession(event)
    }
    return proxyDjangoError(event, error)
  }
})
