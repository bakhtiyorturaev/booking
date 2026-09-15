export const supportedLocales = ["uz", "ru", "en"] as const

export type Locale = typeof supportedLocales[number]

export interface TranslationResponse {
  language: Locale
  translations: Record<string, string>
}
