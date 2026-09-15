export default defineNuxtRouteMiddleware(async (to) => {
  const { isAuthenticated, load } = useAuth()
  await load()
  if (!isAuthenticated.value) {
    return navigateTo({
      path: "/login",
      query: to.fullPath && to.fullPath !== "/" ? { redirect: to.fullPath } : undefined,
    })
  }
})
