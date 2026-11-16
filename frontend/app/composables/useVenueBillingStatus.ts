import type { VenueBillingStatus } from "~/types/venueBilling"

export const billingAlertLevel = (billing: VenueBillingStatus, now: number): VenueBillingStatus["alert_level"] => {
  if (billing.billing_status === "FREE" || billing.billing_enabled === false) return "NONE"
  if (!billing.paid_until) return "NONE"
  const remaining = Date.parse(billing.paid_until) - now
  if (remaining <= 0) return "EXPIRED"
  if (remaining <= 86400000) return "CRITICAL"
  if (remaining <= 5 * 86400000) return "WARNING"
  return "NONE"
}

export const useVenueBillingStatus = (billing: () => VenueBillingStatus) => {
  const clock = useState<number>("venue-billing-clock", () => Date.now())
  const level = computed(() => billingAlertLevel(billing(), clock.value))
  const days = computed(() => billing().paid_until ? Math.max(0, Math.ceil((Date.parse(billing().paid_until!) - clock.value) / 86400000)) : null)
  const label = computed(() => {
    if (billing().billing_status === "FREE" || billing().billing_enabled === false) return "Bepul rejim"
    if (level.value === "EXPIRED") return "Muddat tugagan"
    if (days.value !== null) return `${days.value} kun qoldi`
    return billing().billing_status === "UNCONFIGURED" ? "Tarif belgilanmagan" : "Muddat belgilanmagan"
  })
  // `timeZone` aniq ko'rsatilmasa, `Intl.DateTimeFormat` ishga tushirilgan
  // muhitning tizim vaqt zonasidan foydalanadi — SSR (server, odatda UTC)
  // va brauzer (foydalanuvchining mahalliy zonasi) buni har xil hisoblab,
  // hydration mismatch (server va klient render matni mos kelmasligi)
  // keltirib chiqaradi. Toshkent zonasini aniq belgilab, ikkisida ham bir
  // xil natija chiqishini ta'minlaymiz.
  const expires = computed(() => billing().billing_status !== "FREE" && billing().paid_until ? new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tashkent" }).format(new Date(billing().paid_until!)) : "")
  return { level, days, label, expires }
}
