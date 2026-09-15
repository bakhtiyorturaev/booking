import { useSubscriptionApi } from "~/api/subscription"
import type { SubscriptionStatus } from "~/types/subscription"

export const useSubscription = () => {
  const api = useSubscriptionApi()
  const auth = useAuth()
  const subscription = useState<SubscriptionStatus | null>("current-subscription", () => null)
  const ownerId = useState("subscription-owner", () => "")
  const loaded = useState("subscription-loaded", () => false)
  const now = ref(Date.now())
  const isPaid = computed(() => subscription.value?.plan === "PAID"
    && subscription.value.status === "ACTIVE"
    && Boolean(subscription.value.expires_at)
    && new Date(subscription.value.expires_at!).getTime() > now.value)

  if (import.meta.client) {
    let timer: ReturnType<typeof setInterval> | undefined
    onMounted(() => {
      timer = setInterval(() => { now.value = Date.now() }, 60_000)
    })
    onBeforeUnmount(() => {
      if (timer) clearInterval(timer)
    })
  }

  const load = async (force = false) => {
    const userId = auth.user.value?.id || ""
    if (!userId) {
      subscription.value = null
      ownerId.value = ""
      loaded.value = true
      return null
    }
    if (!force && loaded.value && ownerId.value === userId) return subscription.value
    subscription.value = await api.current()
    ownerId.value = userId
    loaded.value = true
    return subscription.value
  }

  return { subscription, loaded, isPaid, load }
}
