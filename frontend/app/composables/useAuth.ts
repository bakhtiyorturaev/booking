import { useAuthApi } from "~/api/auth"
import { useTranslations } from "~/composables/useTranslations"
import { ApiRequestError } from "~/types/api"
import type { AuthResultData, AuthUser, ChangePasswordPayload, LoginPayload } from "~/types/auth"

import { authScopeForPath, type AuthScope } from "~~/shared/authScope"

export const useAuth = (requestedScope?: AuthScope) => {
  const scope = requestedScope || authScopeForPath(useRoute().path)
  const api = useAuthApi(scope)
  const { locale } = useTranslations()
  const user = useState<AuthUser | null>(`auth-user-${scope}`, () => null)
  const loaded = useState(`auth-loaded-${scope}`, () => false)
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

  const loginWithPassword = async (payload: LoginPayload): Promise<AuthResultData> => {
    const response = await api.login(payload, locale.value)
    user.value = response.data.user
    loaded.value = true
    return response.data
  }

  const changePassword = async (payload: ChangePasswordPayload): Promise<AuthResultData> => {
    const response = await api.changePassword(payload, locale.value)
    if (response.data?.user) {
      user.value = response.data.user
    }
    return response.data
  }

  const logout = async () => {
    await api.logout()
    user.value = null
    loaded.value = true
  }

  return { user, loaded, isAuthenticated, load, setUser, loginWithPassword, changePassword, logout }
}
