import { clearAuthCookies, getAccessToken } from "~~/server/utils/authCookies"
import { djangoRequest } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const access = getAccessToken(event)
  try {
    if (access) {
      await djangoRequest(event, "/auth/logout/", {
        method: "POST",
        headers: { Authorization: `Bearer ${access}` },
      })
    }
  } catch {
    // Local cookies must still be cleared if the backend session already expired.
  } finally {
    clearAuthCookies(event)
  }
  event.node.res.statusCode = 204
})
