import type { BranchZone } from "~/types/club"

export interface AvailabilitySlot {
  starts_at: string
  ends_at: string
  available: number
}

export interface ZoneAvailability extends Pick<
  BranchZone,
  "id" | "name" | "capacity" | "booking_type" | "unit_count" | "price_per_hour_tiyin"
> {
  slots: AvailabilitySlot[]
}

export interface BranchAvailability {
  branch_id: string
  date: string
  zones: ZoneAvailability[]
}

export interface BookingHoldPayload {
  zone_id: string
  starts_at: string
  ends_at: string
  quantity: number
}

export interface BookingHold extends BookingHoldPayload {
  id: string
  unit_price_tiyin: number
  total_price_tiyin: number
  status: string
  expires_at: string
}

export interface Booking {
  id: string
  booking_number: string
  zone_id?: string | null
  zone?: {
    id: string
    name: string
    resource_type: string
    booking_type: "PER_SEAT" | "PER_ZONE"
    branch: {
      id: string
      name: string
      full_address: string
      timezone: string
      club: { id: string, name: string, slug: string }
    }
  } | null
  barber_id?: string | null
  barber?: {
    id: string
    full_name: string
    phone: string
    photo: string | null
    status: string
    status_display: string
    rating: string
    club?: { id: string, name: string, slug: string } | null
    branch?: { id: string, name: string } | null
  } | null
  starts_at: string
  ends_at: string
  quantity: number
  unit_price_tiyin: number
  total_price_tiyin: number
  status: string
  cancellation_reason: string
  created_at: string
}
