import { completePublicAuth } from "~~/server/utils/publicAuth"

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const state = getCookie(event, "telegram_oauth_state")
  const verifier = getCookie(event, "telegram_oauth_verifier")
  deleteCookie(event, "telegram_oauth_state", { path: "/" })
  deleteCookie(event, "telegram_oauth_verifier", { path: "/" })
  if (!state || !verifier || query.state !== state || typeof query.code !== "string") {
    return sendRedirect(event, "/login?telegram=invalid")
  }
  try {
    const redirectUri = `${getRequestURL(event).origin}/api/auth/telegram/callback`
    await completePublicAuth(event, "/auth/telegram/", {
      code: query.code,
      code_verifier: verifier,
      redirect_uri: redirectUri,
      device_name: getRequestHeader(event, "user-agent")?.slice(0, 120) || "",
    })
    return sendRedirect(event, "/")
  } catch {
    return sendRedirect(event, "/login?telegram=failed")
  }
})
