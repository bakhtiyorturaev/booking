import { authScopeForPath, cabinetBase } from "~~/shared/authScope"
export default defineNuxtRouteMiddleware(async (to) => {
  const scope = authScopeForPath(to.path)
  const base = cabinetBase(scope)
  if (to.path === "/cabinet" || to.path.startsWith("/cabinet/")) return navigateTo(base + to.path.slice("/cabinet".length))
  const { isAuthenticated, user, load } = useAuth(scope)
  await load()
  if (!isAuthenticated.value) return navigateTo({ path: `/site/${scope}/login`, query: { redirect: to.fullPath } })
  const staff = user.value?.is_staff || user.value?.is_superuser || ["ADMIN", "MODERATOR"].includes(user.value?.role || "")
  if (scope === "staff" && !staff) return navigateTo("/site/staff/login")
  if (scope === "client" && !staff && user.value?.role !== "CLIENT" && !user.value?.has_barber_profile && !user.value?.has_owned_clubs) return navigateTo("/site/client/login")
  if (!staff && (to.path === base || ["/users", "/payments"].some(suffix => to.path.startsWith(base + suffix)))) return navigateTo(base + (user.value?.has_barber_profile ? "/barbers" : "/clubs"))
})
