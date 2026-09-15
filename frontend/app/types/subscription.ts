export interface SubscriptionStatus {
  plan: "FREE" | "PAID"
  status: "FREE" | "ACTIVE" | "EXPIRED" | "CANCELLED"
  expires_at: string | null
}

export interface SubscriptionPlan {
  code: string
  name: string
  price_tiyin: number
  duration_days: number
}

export interface Payment {
  id: string
  plan: SubscriptionPlan
  amount_tiyin: number
  currency: "UZS"
  status: "PENDING" | "PAID" | "FAILED" | "CANCELLED" | "REFUNDED"
  checkout_url: string
  paid_at: string | null
  created_at: string
}
