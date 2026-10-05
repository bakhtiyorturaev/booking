import { authScopeForPath } from "~~/shared/authScope"
import type { VenueBillingStatus } from "~/types/venueBilling"

export const useCabinetBillingCache = () => {
  const { user } = useAuth()
  return useState<Record<string, VenueBillingStatus>>(`venue-billing-statuses-${authScopeForPath(useRoute().path)}-${user.value?.id || "anonymous"}`, () => ({}))
}
