import { useApiClient } from "~/api/client"
import type {
  ApiSuccess,
  AuthResultData,
  CurrentUserData,
  ProfileUpdatePayload,
  TelegramContactPayload,
  TelegramWebLoginCheckData,
  TelegramWebLoginInitData,
} from "~/types/auth"
import type { Locale } from "~/types/translation"

const languageHeaders = (language: Locale) => ({
  "Accept-Language": language,
})

export const useAuthApi = () => {
  const api = useApiClient()

  return {
    telegramMiniAppLogin: (initData: string, language: Locale) =>
      api.post<ApiSuccess<AuthResultData>>("/api/auth/telegram-miniapp", {
        local: true,
        body: {
          init_data: initData,
          device_name: typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : "",
        },
        headers: languageHeaders(language),
      }),
    saveTelegramContact: (payload: TelegramContactPayload, language: Locale) =>
      api.post<ApiSuccess<{ phone: string; is_phone_verified: boolean; user: AuthResultData["user"] }>>(
        "/api/auth/telegram-contact",
        {
          local: true,
          body: payload,
          headers: languageHeaders(language),
        },
      ),
    initTelegramWebLogin: (language: Locale) =>
      api.post<ApiSuccess<TelegramWebLoginInitData>>("/api/auth/telegram-web-init", {
        local: true,
        headers: languageHeaders(language),
      }),
    checkTelegramWebLogin: (token: string, language: Locale) =>
      api.get<ApiSuccess<TelegramWebLoginCheckData>>(`/api/auth/telegram-web-check?token=${encodeURIComponent(token)}`, {
        local: true,
        headers: languageHeaders(language),
      }),
    session: () =>
      api.get<ApiSuccess<CurrentUserData>>("/api/auth/session", {
        local: true,
      }),
    updateProfile: (payload: ProfileUpdatePayload, language: Locale) =>
      api.patch<ApiSuccess<CurrentUserData>>("/api/profile", {
        local: true,
        body: payload,
        headers: languageHeaders(language),
      }),
    refresh: () =>
      api.post<{ success: true }>("/api/auth/refresh", {
        local: true,
      }),
    logout: () => api.post<unknown>("/api/auth/logout", { local: true }),
  }
}
