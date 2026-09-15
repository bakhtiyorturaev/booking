export default defineNuxtRouteMiddleware(async (to) => {
  const { isAuthenticated, user, load } = useAuth()
  await load()

  if (!isAuthenticated.value) {
    return navigateTo({
      path: "/login",
      query: to.fullPath && to.fullPath !== "/" ? { redirect: to.fullPath } : undefined,
    })
  }

  const role = user.value?.role
  const isStaffRole = role === "ADMIN" || role === "MODERATOR"

  if (!isStaffRole) {
    return navigateTo("/")
  }
})
