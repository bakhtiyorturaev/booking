import { useApiClient } from "~/api/client"
import type { Payment, SubscriptionPlan, SubscriptionStatus } from "~/types/subscription"

export const useSubscriptionApi = () => {
  const api = useApiClient()
  return {
    current: () => api.get<SubscriptionStatus>("/api/subscription", { local: true }),
    plans: () => api.get<SubscriptionPlan[]>("/api/subscription-plans", { local: true }),
    checkout: (planCode: string, idempotencyKey: string) =>
      api.post<Payment>("/api/payment-checkout", {
        local: true,
        headers: { "Idempotency-Key": idempotencyKey },
        body: { plan_code: planCode },
      }),
  }
}
