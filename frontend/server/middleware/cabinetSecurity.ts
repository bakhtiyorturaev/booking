export default defineEventHandler((event) => {
  const privatePath = ["/api/cabinet/", "/api/auth/", "/cabinet", "/site/staff/", "/site/client/", "/api/profile", "/api/bookings", "/api/booking-holds", "/api/favorites", "/api/payment-checkout"].some(prefix => event.path.startsWith(prefix))
  const writes = !["GET", "HEAD", "OPTIONS"].includes(event.method)
  if (!privatePath && !(writes && event.path.startsWith("/api/"))) return
  setResponseHeader(event, "Cache-Control", "private, no-store")
  setResponseHeader(event, "X-Content-Type-Options", "nosniff")
  setResponseHeader(event, "X-Frame-Options", "DENY")
  setResponseHeader(event, "Referrer-Policy", "same-origin")
  if (!writes) return

  const origin = getRequestHeader(event, "origin")
  const referer = getRequestHeader(event, "referer")
  const fetchSite = getRequestHeader(event, "sec-fetch-site")
  const trustProxy = String(useRuntimeConfig().trustProxyHeaders) === "true"
  const expectedOrigin = `${getRequestProtocol(event, { xForwardedProto: trustProxy })}://${getRequestHost(event, { xForwardedHost: false })}`
  let actualOrigin = ""
  try {
    actualOrigin = new URL(origin || referer || "").origin
  } catch {
    // Requests without browser origin information are rejected for cookie-based writes.
  }
  if (fetchSite === "cross-site" || actualOrigin !== expectedOrigin) {
    throw createError({ statusCode: 403, statusMessage: "Origin not allowed" })
  }
})
