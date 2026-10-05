import type { AuthScope } from "~~/shared/authScope"
import { useApiClient } from "~/api/client"
import type {
  ApiSuccess,
  AuthResultData,
  ChangePasswordPayload,
  CurrentUserData,
  LoginPayload,
  ProfileUpdatePayload,
  TelegramCodeInitData,
  TelegramCodeVerifyPayload,
  TelegramContactPayload,
  TelegramWebLoginCheckData,
  TelegramWebLoginInitData,
} from "~/types/auth"
import type { Locale } from "~/types/translation"

const languageHeaders = (language: Locale) => ({
  "Accept-Language": language,
})

export const useAuthApi = (scope?: AuthScope) => {
  const client = useApiClient()
  const api = {
    get: <T>(path: string, options: Parameters<typeof client.get>[1] = {}) => client.get<T>(path, { ...options, headers: { ...Object.fromEntries(new Headers(options.headers)), ...(scope ? { "X-Auth-Scope": scope } : {}) } }),
    post: <T>(path: string, options: Parameters<typeof client.post>[1] = {}) => client.post<T>(path, { ...options, headers: { ...Object.fromEntries(new Headers(options.headers)), ...(scope ? { "X-Auth-Scope": scope } : {}) } }),
    patch: <T>(path: string, options: Parameters<typeof client.patch>[1] = {}) => client.patch<T>(path, { ...options, headers: { ...Object.fromEntries(new Headers(options.headers)), ...(scope ? { "X-Auth-Scope": scope } : {}) } }),
  }

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
    initTelegramCodeLogin: (language: Locale) =>
      api.post<ApiSuccess<TelegramCodeInitData>>("/api/auth/telegram-code-init", {
        local: true,
        headers: languageHeaders(language),
      }),
    verifyTelegramCode: (payload: TelegramCodeVerifyPayload, language: Locale) =>
      api.post<ApiSuccess<AuthResultData>>("/api/auth/telegram-code-verify", {
        local: true,
        body: {
          ...payload,
          device_name: payload.device_name || (typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : ""),
        },
        headers: languageHeaders(language),
      }),
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
    login: (payload: LoginPayload, language: Locale) =>
      api.post<ApiSuccess<AuthResultData>>("/api/auth/login", {
        local: true,
        body: {
          ...payload,
          device_name: payload.device_name || (typeof navigator !== "undefined" ? navigator.userAgent.slice(0, 120) : ""),
        },
        headers: languageHeaders(language),
      }),
    changePassword: (payload: ChangePasswordPayload, language: Locale) =>
      api.post<ApiSuccess<AuthResultData>>("/api/auth/change-password", {
        local: true,
        body: payload,
        headers: languageHeaders(language),
      }),
    logout: () => api.post<unknown>("/api/auth/logout", { local: true }),
  }
}
