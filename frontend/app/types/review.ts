export interface PublicReview {
  id: string
  author: string
  rating: number
  comment: string
  created_at: string
}

export interface Review {
  id: string
  booking_id: string
  club_id: string
  rating: number
  comment: string
  created_at: string
  updated_at: string
}

export interface ReviewPayload {
  booking_id: string
  rating: number
  comment: string
}
