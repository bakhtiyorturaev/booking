import { authenticatedDjangoRequest } from "~~/server/utils/authenticatedDjango"
import { proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    return await authenticatedDjangoRequest(event, "/auth/telegram-miniapp/contact/", {
      method: "POST",
      body,
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})

