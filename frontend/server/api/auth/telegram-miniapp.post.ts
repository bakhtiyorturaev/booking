import { proxyDjangoError } from "~~/server/utils/django"
import { completePublicAuth } from "~~/server/utils/publicAuth"

export default defineEventHandler(async (event) => {
  try {
    return await completePublicAuth(
      event,
      "/auth/telegram-miniapp/",
      await readBody(event),
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
