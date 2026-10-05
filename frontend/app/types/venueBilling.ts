export interface Paginated<T> { count: number; next: string | null; previous: string | null; results: T[] }
export interface VenueBillingStatus {
  is_free?: boolean
  monthly_price_tiyin: number | null
  paid_until: string | null
  billing_status: "UNCONFIGURED" | "UNPAID" | "ACTIVE" | "EXPIRED" | "FREE"
  billing_enabled?: boolean
  grace_until?: string | null
  remaining_days: number | null
  alert_level: "NONE" | "WARNING" | "CRITICAL" | "EXPIRED"
}
export interface BillingVenue extends VenueBillingStatus {
  club_id?: string
  club_name?: string
  id: string
  name: string
  category: string
  owner: string
  owner_name: string
}
export interface ManualVenuePayment {
  id: string
  club: string | null
  barber: string | null
  barber_name: string
  club_name: string
  client_name: string
  received_by_name: string
  amount_tiyin: number
  monthly_price_tiyin: number
  method: "CASH" | "CARD"
  duration_days: string
  period_starts_at: string
  period_ends_at: string
  created_at: string
  note: string
}
export interface ManualPaymentInput { club?: string; barber?: string; amount: string; method: "CASH" | "CARD"; note: string; idempotency_key: string }
export interface BillingSummary { total_tiyin: number; today_tiyin: number; cash_tiyin: number; card_tiyin: number; count: number }
