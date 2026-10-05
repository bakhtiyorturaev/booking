import { djangoRequest, proxyDjangoError } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    return await djangoRequest(event, "/auth/telegram/code/status/", {
      method: "POST",
      body: await readBody(event),
    })
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
