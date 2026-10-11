export default defineEventHandler((event) => {
  setResponseHeader(event, "X-Content-Type-Options", "nosniff")
  setResponseHeader(event, "Referrer-Policy", "same-origin")

  const config = useRuntimeConfig()
  const maxAge = Number(config.hstsSeconds)
  const trustProxy = String(config.trustProxyHeaders) === "true"
  if (!Number.isSafeInteger(maxAge) || maxAge <= 0) return
  if (getRequestProtocol(event, { xForwardedProto: trustProxy }) !== "https") return

  const directives = [`max-age=${maxAge}`]
  if (String(config.hstsIncludeSubdomains) === "true") directives.push("includeSubDomains")
  if (String(config.hstsPreload) === "true") directives.push("preload")
  setResponseHeader(event, "Strict-Transport-Security", directives.join("; "))
})
