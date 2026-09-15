import { useApiClient } from "~/api/client"
import type { Locale, TranslationResponse } from "~/types/translation"

export const useTranslationApi = () => {
  const api = useApiClient()

  return {
    list: (language: Locale) => api.get<TranslationResponse>("/api/translations", {
      local: true,
      query: { lang: language },
    }),
  }
}
