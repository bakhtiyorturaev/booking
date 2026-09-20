export interface LocationOption {
  id: string
  name: string
  slug: string
}

export interface BranchSummary {
  id: string
  name: string
  address: string
  full_address: string
  city: LocationOption
  district: LocationOption | null
  latitude: string
  longitude: string
  is_24_hours: boolean
  service_types: string[]
  min_price_tiyin: number | null
  cover_image: string | null
  distance_km: number | null
}

export interface ClubBrief {
  id: string
  name: string
  category?: "GAMING_CLUB" | "BARBERSHOP"
  category_display?: string
  slug: string
  logo: string | null
  rating: string
  review_count: number
}

export interface BranchListSummary extends BranchSummary {
  club: ClubBrief
  is_favorite?: boolean
}

export interface FavoriteItem {
  id: string
  club: ClubSummary
}

export interface BranchZone {
  id: string
  name: string
  description: string
  capacity: number
  booking_type: "PER_SEAT" | "PER_ZONE"
  unit_count: number
  price_per_hour_tiyin: number
  resource_type: string
}

export interface OperatingHour {
  weekday: number
  weekday_name: string
  opens_at: string | null
  closes_at: string | null
  is_closed: boolean
}

export interface BranchDetail extends BranchSummary {
  club: ClubBrief
  description: string
  landmark: string
  phone: string
  timezone: string
  slot_interval_minutes: number
  minimum_booking_minutes: number
  maximum_booking_minutes: number
  booking_hold_minutes: number
  advance_booking_days: number
  free_cancellation_minutes: number
  no_show_grace_minutes: number
  auto_confirm_booking: boolean
  images: { image: string, is_cover: boolean }[]
  operating_hours: OperatingHour[]
  zones: BranchZone[]
}

export interface ClubSummary {
  id: string
  name: string
  category?: "GAMING_CLUB" | "BARBERSHOP"
  category_display?: string
  slug: string
  description: string
  logo: string | null
  cover: string | null
  is_verified: boolean
  rating: string
  review_count: number
  service_types: string[]
  min_price_tiyin: number | null
  distance_km: number | null
  is_favorite: boolean
  branches: BranchSummary[]
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
