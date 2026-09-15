import type { SubscriptionPlan } from "~~/app/types/subscription"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  try {
    return await djangoRequest<SubscriptionPlan[]>(event, "/subscriptions/plans/", {
      headers: { "Accept-Language": requestLanguage(event) },
    })
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
