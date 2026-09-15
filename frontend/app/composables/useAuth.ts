import { useAuthApi } from "~/api/auth"
import { ApiRequestError } from "~/types/api"
import type { AuthUser } from "~/types/auth"

export const useAuth = () => {
  const api = useAuthApi()
  const user = useState<AuthUser | null>("auth-user", () => null)
  const loaded = useState("auth-loaded", () => false)
  const isAuthenticated = computed(() => Boolean(user.value))

  const load = async (force = false) => {
    if (loaded.value && !force) return user.value
    try {
      const response = await api.session()
      user.value = response.data.user
    } catch (error) {
      if (!(error instanceof ApiRequestError) || error.statusCode !== 401) throw error
      user.value = null
    }
    loaded.value = true
    return user.value
  }

  const setUser = (value: AuthUser) => {
    user.value = value
    loaded.value = true
  }

  const logout = async () => {
    await api.logout()
    user.value = null
    loaded.value = true
  }

  return { user, loaded, isAuthenticated, load, setUser, logout }
}
