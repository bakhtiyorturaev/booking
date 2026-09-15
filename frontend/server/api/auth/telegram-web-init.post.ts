import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    return await djangoRequest(event, "/auth/telegram-web/init/", {
      method: "POST",
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
