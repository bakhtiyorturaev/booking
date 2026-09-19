<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faCalendarCheck,
  faClock,
  faHourglassHalf,
  faLocationDot,
  faPen,
  faStar,
  faTicket,
  faTrash,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"

import { useBookingsApi } from "~/api/bookings"
import { useReviewsApi } from "~/api/reviews"
import { ApiRequestError } from "~/types/api"
import type { Booking } from "~/types/booking"
import type { Review } from "~/types/review"
import { useToast } from "~/composables/useToast"

definePageMeta({ layout: "customer", middleware: "auth" })

const toast = useToast()

const bookingsApi = useBookingsApi()
const reviewsApi = useReviewsApi()
const subscriptionState = useSubscription()
const { locale, load, t } = useTranslations()
await load()
await subscriptionState.load().catch(() => null)

useHead({
  title: computed(() => t("bookings.title") || "Mening bronlarim"),
})

type BookingScope = "all" | "upcoming" | "past"
const scope = ref<BookingScope>("all")
const { data, error, status, refresh } = await useAsyncData(
  "my-bookings",
  () => bookingsApi.list(scope.value),
  { watch: [scope] },
)
const bookings = computed(() => data.value?.results ?? [])
const { data: reviewData, refresh: refreshReviews } = await useAsyncData(
  "my-reviews",
  () => reviewsApi.mine(),
)
const reviews = computed(() => reviewData.value?.results ?? [])
const reviewByBooking = computed(() => new Map(
  reviews.value.map(review => [review.booking_id, review]),
))
const cancelTarget = ref<string>()
const cancelReason = ref("")
const cancelling = ref(false)
const actionMessage = ref("")
const reviewTarget = ref<string>()
const reviewRating = ref(0)
const reviewComment = ref("")
const reviewSaving = ref(false)
const deleteTarget = ref<string>()

const statusCodes: Record<string, string> = {
  PENDING_CONFIRMATION: "bookings.status_pending",
  CONFIRMED: "bookings.status_confirmed",
  CHECKED_IN: "bookings.status_checked_in",
  COMPLETED: "bookings.status_completed",
  CANCELLED: "bookings.status_cancelled",
  NO_SHOW: "bookings.status_no_show",
}
const canCancel = (booking: Booking) =>
  ["PENDING_CONFIRMATION", "CONFIRMED"].includes(booking.status)
const formatDateTime = (value: string, timeZone: string) => {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date(value))
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find(item => item.type === type)?.value || ""
  return `${part("day")}.${part("month")}.${part("year")} · ${part("hour")}:${part("minute")}`
}
const formatPrice = (value: number) =>
  `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`
const formatDuration = (startsAt: string, endsAt: string) => {
  const minutes = Math.round(
    (new Date(endsAt).getTime() - new Date(startsAt).getTime()) / 60_000,
  )
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  if (!hours) return t("branches.duration_minutes", { minutes: remainder })
  return remainder
    ? t("bookings.duration_hours_minutes", { hours, minutes: remainder })
    : t("bookings.duration_hours", { hours })
}

const startCancellation = (booking: Booking) => {
  cancelTarget.value = booking.id
  cancelReason.value = ""
  actionMessage.value = ""
}

const closeCancellation = () => {
  cancelTarget.value = undefined
  cancelReason.value = ""
}

const cancelBooking = async (booking: Booking) => {
  if (!cancelReason.value.trim() || cancelling.value) return
  cancelling.value = true
  actionMessage.value = ""
  try {
    await bookingsApi.cancel(booking.id, cancelReason.value.trim())
    closeCancellation()
    const successMsg = t("bookings.cancel_success")
    actionMessage.value = successMsg
    toast.success(successMsg)
    await refresh()
  } catch (error) {
    const errText = error instanceof ApiRequestError ? error.message : t("common.backend_unavailable")
    actionMessage.value = errText
    toast.error(errText)
  } finally {
    cancelling.value = false
  }
}

const startReview = (booking: Booking, review?: Review) => {
  reviewTarget.value = booking.id
  reviewRating.value = review?.rating ?? 0
  reviewComment.value = review?.comment ?? ""
  deleteTarget.value = undefined
  actionMessage.value = ""
}

const closeReview = () => {
  reviewTarget.value = undefined
  reviewRating.value = 0
  reviewComment.value = ""
}

const saveReview = async (booking: Booking) => {
  if (!reviewRating.value || reviewSaving.value || !subscriptionState.isPaid.value) return
  reviewSaving.value = true
  actionMessage.value = ""
  try {
    const existing = reviewByBooking.value.get(booking.id)
    const payload = { rating: reviewRating.value, comment: reviewComment.value.trim() }
    if (existing) await reviewsApi.update(existing.id, payload)
    else await reviewsApi.create({ booking_id: booking.id, ...payload })
    closeReview()
    const successMsg = t(existing ? "reviews.update_success" : "reviews.create_success")
    actionMessage.value = successMsg
    toast.success(successMsg)
    await refreshReviews()
  } catch (error) {
    const errText = error instanceof ApiRequestError ? error.message : t("common.backend_unavailable")
    actionMessage.value = errText
    toast.error(errText)
  } finally {
    reviewSaving.value = false
  }
}

const deleteReview = async (review: Review) => {
  if (deleteTarget.value !== review.id) {
    deleteTarget.value = review.id
    return
  }
  reviewSaving.value = true
  actionMessage.value = ""
  try {
    await reviewsApi.remove(review.id)
    deleteTarget.value = undefined
    closeReview()
    const successMsg = t("reviews.delete_success")
    actionMessage.value = successMsg
    toast.success(successMsg)
    await refreshReviews()
  } catch (error) {
    const errText = error instanceof ApiRequestError ? error.message : t("common.backend_unavailable")
    actionMessage.value = errText
    toast.error(errText)
  } finally {
    reviewSaving.value = false
  }
}
</script>

<template>
  <section class="bookings-page">
    <header class="bookings-heading">
      <h1>{{ t("bookings.my_bookings") }}</h1>
      <div class="booking-tabs">
        <button
          v-for="item in (['all', 'upcoming', 'past'] as BookingScope[])"
          :key="item"
          type="button"
          :class="{ active: scope === item }"
          @click="scope = item"
        >
          {{ t({ all: "bookings.filter_all", upcoming: "bookings.filter_upcoming", past: "bookings.filter_past" }[item]) }}
        </button>
      </div>
    </header>

    <p v-if="actionMessage" class="bookings-action-message" role="status">{{ actionMessage }}</p>

    <div v-if="status === 'pending'" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faCalendarCheck" /></span>
      <p>{{ t("bookings.loading") }}</p>
    </div>
    <div v-else-if="error" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faCalendarCheck" /></span>
      <p class="form-message">{{ error.message }}</p>
    </div>
    <div v-else-if="!bookings.length" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faCalendarCheck" /></span>
      <p>{{ t("bookings.no_bookings") }}</p>
    </div>

    <div v-else class="booking-list">
      <article v-for="booking in bookings" :key="booking.id" class="booking-card">
        <div class="booking-card-top">
          <div>
            <span class="booking-number"><FontAwesomeIcon :icon="faTicket" />{{ booking.booking_number }}</span>
            
            <!-- Zone Booking (Gaming Club) -->
            <template v-if="booking.zone">
              <h2>{{ booking.zone.name }}</h2>
              <div class="booking-type-badges">
                <span>{{ t(booking.zone.resource_type === "PLAYSTATION" ? "clubs.service_playstation" : "clubs.service_pc") }}</span>
                <span v-if="booking.zone.booking_type === 'PER_ZONE'" class="vip">{{ t("branches.zone_type_vip") }}</span>
              </div>
              <NuxtLink :to="`/branches/${booking.zone.branch.id}`">
                {{ booking.zone.branch.name }}
              </NuxtLink>
            </template>

            <!-- Barber Booking (Barbershop) -->
            <template v-else-if="booking.barber">
              <h2>✂️ {{ booking.barber.full_name }}</h2>
              <div class="booking-type-badges">
                <span>💈 {{ t("barbers.barbershop") }}</span>
              </div>
              <span class="barber-salon-link">
                {{ booking.barber.club?.name || t("barbers.barbershop") }}
                <small v-if="booking.barber.branch?.name">({{ booking.barber.branch.name }})</small>
              </span>
            </template>
          </div>

          <span class="booking-status" :class="booking.status.toLowerCase()">
            {{ t(statusCodes[booking.status] || "common.free") }}
          </span>
        </div>

        <div class="booking-card-details">
          <span>
            <FontAwesomeIcon :icon="faClock" />
            <span class="booking-period">
              <span><small>{{ t("bookings.starts_at") }}</small>{{ formatDateTime(booking.starts_at, booking.zone?.branch?.timezone || 'Asia/Tashkent') }}</span>
              <span><small>{{ t("bookings.ends_at") }}</small>{{ formatDateTime(booking.ends_at, booking.zone?.branch?.timezone || 'Asia/Tashkent') }}</span>
            </span>
          </span>
          <span v-if="booking.zone?.branch?.full_address">
            <FontAwesomeIcon :icon="faLocationDot" />{{ booking.zone.branch.full_address }}
          </span>
          <span>
            <FontAwesomeIcon :icon="faHourglassHalf" />
            {{ t("bookings.duration") }}: {{ formatDuration(booking.starts_at, booking.ends_at) }}
          </span>
        </div>

        <div class="booking-card-footer">
          <strong v-if="booking.total_price_tiyin > 0">{{ formatPrice(booking.total_price_tiyin) }}</strong>
          <strong v-else class="pay-onsite-text">{{ t("barbers.pay_on_site") }}</strong>
          <div>
            <button v-if="canCancel(booking)" type="button" @click="startCancellation(booking)">
              {{ t("bookings.cancel_btn") }}
            </button>
            <template v-if="booking.status === 'COMPLETED'">
              <button
                v-if="reviewByBooking.get(booking.id) && subscriptionState.isPaid.value"
                type="button"
                class="review-action"
                @click="startReview(booking, reviewByBooking.get(booking.id))"
              >
                <FontAwesomeIcon :icon="faPen" />{{ t("reviews.edit_review") }}
              </button>
              <button
                v-else-if="subscriptionState.isPaid.value"
                type="button"
                class="review-action"
                @click="startReview(booking)"
              >
                <FontAwesomeIcon :icon="faStar" />{{ t("reviews.write_review") }}
              </button>
              <span v-else class="review-paid-note">{{ t("reviews.paid_only_note") }}</span>
            </template>
          </div>
        </div>

        <div v-if="reviewByBooking.get(booking.id) && reviewTarget !== booking.id" class="my-review-summary">
          <span class="review-stars" :aria-label="t('reviews.rating_stars', { rating: reviewByBooking.get(booking.id)?.rating || 0 })">
            <FontAwesomeIcon
              v-for="value in 5"
              :key="value"
              :icon="faStar"
              :class="{ active: value <= (reviewByBooking.get(booking.id)?.rating || 0) }"
            />
          </span>
          <p v-if="reviewByBooking.get(booking.id)?.comment">{{ reviewByBooking.get(booking.id)?.comment }}</p>
        </div>

        <form
          v-if="reviewTarget === booking.id"
          class="booking-review-form"
          @submit.prevent="saveReview(booking)"
        >
          <span>{{ t("reviews.your_rating") }}</span>
          <div class="review-rating-input">
            <button
              v-for="value in 5"
              :key="value"
              type="button"
              :class="{ active: value <= reviewRating }"
              :aria-label="t('reviews.rating_stars', { rating: value })"
              @click="reviewRating = value"
            >
              <FontAwesomeIcon :icon="faStar" />
            </button>
          </div>
          <label>
            <span>{{ t("reviews.comment_label") }}</span>
            <textarea v-model="reviewComment" maxlength="1000" :placeholder="t('reviews.comment_placeholder')" />
          </label>
          <div class="review-form-actions">
            <button type="button" @click="closeReview"><FontAwesomeIcon :icon="faXmark" />{{ t("common.cancel") }}</button>
            <button
              v-if="reviewByBooking.get(booking.id)"
              type="button"
              class="review-delete"
              :disabled="reviewSaving"
              @click="deleteReview(reviewByBooking.get(booking.id)!)"
            >
              <FontAwesomeIcon :icon="faTrash" />
              {{ t(deleteTarget === reviewByBooking.get(booking.id)?.id ? "reviews.delete_confirm" : "reviews.delete_btn") }}
            </button>
            <button type="submit" :disabled="!reviewRating || reviewSaving">
              {{ t(reviewSaving ? "reviews.saving" : "common.save") }}
            </button>
          </div>
        </form>

        <form
          v-if="cancelTarget === booking.id"
          class="booking-cancel-form"
          @submit.prevent="cancelBooking(booking)"
        >
          <label>
            <span>{{ t("bookings.cancel_reason") }}</span>
            <textarea v-model="cancelReason" maxlength="500" required />
          </label>
          <div>
            <button type="button" @click="closeCancellation">
              <FontAwesomeIcon :icon="faXmark" />{{ t("common.cancel") }}
            </button>
            <button type="submit" :disabled="!cancelReason.trim() || cancelling">
              {{ t(cancelling ? "bookings.cancelling" : "bookings.cancel_btn") }}
            </button>
          </div>
        </form>
      </article>
    </div>
  </section>
</template>
