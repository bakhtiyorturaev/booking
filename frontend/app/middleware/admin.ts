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
  if (!staff) {
    const sections = user.value?.cabinet_sections || []
    const section = to.path.slice(base.length).split("/")[1] || ""
    const destination = sections.includes("barbers") && !sections.includes("clubs") ? "/barbers" : sections.includes("clubs") ? "/clubs" : "/bookings"
    if (section !== "bookings" && !sections.includes(section)) return navigateTo(base + destination)
  }
  if (to.path === base + "/users") return navigateTo(base + "/users/customers")
})
