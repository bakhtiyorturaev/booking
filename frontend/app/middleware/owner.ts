export default defineNuxtRouteMiddleware(async (to) => {
  const { isAuthenticated, user, load } = useAuth()
  await load()

  if (!isAuthenticated.value) {
    return navigateTo({
      path: "/login",
      query: to.fullPath && to.fullPath !== "/" ? { redirect: to.fullPath } : undefined,
    })
  }

  // Egalar kabinetiga muassasa egasi yoki platforma admini/moderatori kira oladi.
  const role = user.value?.role
  const isPlatformStaff = role === "ADMIN" || role === "MODERATOR"
  const isOwner = user.value?.is_club_owner === true

  if (!isPlatformStaff && !isOwner) {
    return navigateTo("/")
  }
})
