export const useCabinetAccess = () => {
  const route = useRoute()
  const { user } = useAuth()
  const isStaff = computed(() => !route.path.startsWith('/site/client/') && Boolean(
    user.value?.is_staff || user.value?.is_superuser || ['ADMIN', 'MODERATOR'].includes(user.value?.role || ''),
  ))
  return { isStaff }
}
