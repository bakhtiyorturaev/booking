import { authScopeForPath, cabinetBase } from "~~/shared/authScope"
export default defineNuxtRouteMiddleware(async (to) => {
  const scope = authScopeForPath(to.path)
  const { isAuthenticated, load } = useAuth(scope)
  await load()
  if (isAuthenticated.value) {
    const base = scope === "customer" ? "/" : cabinetBase(scope)
    const requested = to.query.redirect
    const target = typeof requested === "string" && requested.startsWith("/") && !requested.startsWith("//") && !requested.includes("\\") && (scope === "customer" ? !requested.startsWith("/site/") && !requested.startsWith("/cabinet") : requested === base || requested.startsWith(base + "/")) ? requested : base
    return navigateTo(target)
  }
})
