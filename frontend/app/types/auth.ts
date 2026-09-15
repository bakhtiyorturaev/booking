import type { Locale } from "~/types/translation"

export interface ApiSuccess<T> {
  success: true
  code: string
  message: string
  data: T
}

export interface AuthUser {
  id: string
  username: string
  role: string
  full_name?: string
  avatar_url?: string
  preferred_language?: Locale
  is_profile_completed?: boolean
  phone?: string | null
  telegram_user_id?: number | null
  is_phone_verified?: boolean
  profile?: UserProfileData
}

export interface UserProfileData {
  full_name: string
  avatar_url: string
  birth_date: string | null
  preferred_language: Locale
  city: string
  telegram_notifications_enabled: boolean
  is_profile_completed: boolean
}

export interface ProfileUpdatePayload {
  full_name?: string
  birth_date?: string | null
  city?: string
  preferred_language?: Locale
}

export interface AuthResultData {
  user: AuthUser
  is_new_user: boolean
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface BackendAuthResultData extends AuthResultData {
  tokens: AuthTokens
}

export interface CurrentUserData {
  user: AuthUser
}

export interface TelegramWebLoginInitData {
  token: string
  bot_username: string
  deep_link: string
  expires_in: number
}

export interface TelegramWebLoginCheckData {
  status: "PENDING" | "SUCCESS" | "BLOCKED"
  user?: AuthUser
  is_new_user?: boolean
}

export interface TelegramContactPayload {
  phone: string
}
