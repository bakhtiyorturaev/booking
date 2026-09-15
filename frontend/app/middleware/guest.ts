export default defineNuxtRouteMiddleware(async (to) => {
  const { isAuthenticated, load } = useAuth()
  await load()
  if (isAuthenticated.value) {
    const target = typeof to.query.redirect === "string" && to.query.redirect ? to.query.redirect : "/"
    return navigateTo(target)
  }
})
