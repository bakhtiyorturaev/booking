import { createHash, randomBytes } from "node:crypto"

import type { ApiSuccess } from "~~/app/types/auth"
import { djangoRequest } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const config = await djangoRequest<ApiSuccess<{ client_id: string }>>(
    event,
    "/auth/telegram/config/",
  )
  const state = randomBytes(32).toString("base64url")
  const verifier = randomBytes(48).toString("base64url")
  const challenge = createHash("sha256").update(verifier).digest("base64url")
  const secure = getRequestProtocol(event) === "https"
  const cookieOptions = { httpOnly: true, secure, sameSite: "lax" as const, maxAge: 600, path: "/" }
  setCookie(event, "telegram_oauth_state", state, cookieOptions)
  setCookie(event, "telegram_oauth_verifier", verifier, cookieOptions)

  const origin = getRequestURL(event).origin
  const redirectUri = `${origin}/api/auth/telegram/callback`
  const url = new URL("https://oauth.telegram.org/auth")
  url.searchParams.set("client_id", config.data.client_id)
  url.searchParams.set("redirect_uri", redirectUri)
  url.searchParams.set("response_type", "code")
  url.searchParams.set("scope", "openid profile phone telegram:bot_access")
  url.searchParams.set("state", state)
  url.searchParams.set("code_challenge", challenge)
  url.searchParams.set("code_challenge_method", "S256")
  return sendRedirect(event, url.toString())
})
