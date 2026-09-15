export type BarberStatus = "AVAILABLE" | "BREAK" | "NOT_AT_WORK" | "DAY_OFF"
export type AffiliationStatus = "NONE" | "PENDING" | "APPROVED" | "REJECTED"

export interface BarberSlot {
  starts_at: string
  ends_at: string
  time_label: string
  hour: number
  is_available: boolean
  is_past: boolean
  is_occupied: boolean
}

export interface BarberAvailability {
  barber_id: string
  target_date: string
  is_available: boolean
  status: BarberStatus
  reason: string
  slots: BarberSlot[]
}

export interface BarberItem {
  id: string
  full_name: string
  phone: string
  photo: string | null
  status: BarberStatus
  status_display: string
  rating: string
  review_count: number
  club_id: string | null
  club_name: string
  club_slug: string
  branch_id: string | null
  branch_name: string
  branch_address?: string
  branch_city?: string
  branch_district?: string
  distance_km?: number | null
  work_start_time: string
  work_end_time: string
  working_days: number[]
}

export interface BarberProfile {
  id: string
  full_name: string
  phone: string
  photo: string | null
  status: BarberStatus
  status_display: string
  affiliation_status: AffiliationStatus
  affiliation_status_display: string
  club_id: string | null
  club_name: string
  branch_id: string | null
  branch_name: string
  work_start_time: string
  work_end_time: string
  working_days: number[]
  rating: string
  review_count: number
  is_active: boolean
}

export interface CabinetBarberItem {
  id: string
  user_id: string
  user_phone: string
  full_name: string
  phone: string
  photo: string | null
  status: BarberStatus
  status_display: string
  affiliation_status: AffiliationStatus
  affiliation_status_display: string
  club_id: string | null
  club_name: string
  branch_id: string | null
  branch_name: string
  work_start_time: string
  work_end_time: string
  working_days: number[]
  rating: string
  review_count: number
  is_active: boolean
  created_at: string
}
