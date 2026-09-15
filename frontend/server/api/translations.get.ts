import type { ApiErrorData } from "~~/app/types/api"
import {
  supportedLocales,
  type Locale,
  type TranslationResponse,
} from "~~/app/types/translation"
import { djangoRequest, proxyDjangoError } from "~~/server/utils/django"

export default defineEventHandler(async (event): Promise<TranslationResponse | ApiErrorData> => {
  const requested = getQuery(event).lang
  const language = supportedLocales.includes(requested as Locale)
    ? requested as Locale
    : "uz"

  try {
    return await djangoRequest<TranslationResponse>(event, "/", {
      query: { lang: language },
    }) as TranslationResponse
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
