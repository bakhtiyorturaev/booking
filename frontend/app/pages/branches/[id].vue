<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faArrowLeft,
  faCalendarDays,
  faCheck,
  faCircleCheck,
  faClock,
  faComputer,
  faCreditCard,
  faGamepad,
  faImages,
  faLocationDot,
  faStar,
  faStore,
  faUsers,
} from "@fortawesome/free-solid-svg-icons"

import { useBookingsApi } from "~/api/bookings"
import { useBranchesApi } from "~/api/branches"
import { useReviewsApi } from "~/api/reviews"
import { useBarbersApi } from "~/api/barbers"
import { ApiRequestError } from "~/types/api"
import type { Booking } from "~/types/booking"
import type { BarberItem } from "~/types/barber"
import BranchCard from "~/components/catalog/BranchCard.vue"
import BarberCard from "~/components/catalog/BarberCard.vue"
import BarberBookingModal from "~/components/catalog/BarberBookingModal.vue"
import TelegramAuthModal from "~/components/auth/TelegramAuthModal.vue"
import TelegramContactModal from "~/components/auth/TelegramContactModal.vue"

definePageMeta({ layout: "customer" })

const dateInTimezone = (timeZone: string) => {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts()
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find(item => item.type === type)?.value || ""
  return `${part("year")}-${part("month")}-${part("day")}`
}

const addDays = (date: string, days: number) => {
  const value = new Date(`${date}T00:00:00Z`)
  value.setUTCDate(value.getUTCDate() + days)
  return value.toISOString().slice(0, 10)
}

const route = useRoute()
const branchesApi = useBranchesApi()
const bookingsApi = useBookingsApi()
const reviewsApi = useReviewsApi()
const barbersApi = useBarbersApi()
const auth = useAuth()
const subscriptionState = useSubscription()
const { locale, load, t } = useTranslations()
await load()
if (["clubs.all_clubs", "branches.title", "branches.zones_title", "reviews.title", "auth.unauthorized"].some(code => t(code) === code)) await load(locale.value, true)
await auth.load().catch(() => null)
if (auth.isAuthenticated.value) {
  await subscriptionState.load().catch(() => null)
}

const selectedBarber = ref<BarberItem | null>(null)
const showBarberModal = ref(false)

const openBarberModal = (barber: BarberItem) => {
  selectedBarber.value = barber
  showBarberModal.value = true
}

const id = computed(() => String(route.params.id || ""))
const { data, error, status } = await useAsyncData(
  () => `branch-${id.value}`,
  async () => {
    const branch = await branchesApi.get(id.value)
    const initialDate = dateInTimezone(branch.timezone)
    const [related, reviews, initialAvail, barbersRes] = await Promise.all([
      branchesApi.list({
        category: branch.club.category,
        latitude: branch.latitude !== null && branch.latitude !== undefined ? Number(branch.latitude) : undefined,
        longitude: branch.longitude !== null && branch.longitude !== undefined ? Number(branch.longitude) : undefined,
        ordering: branch.latitude !== null ? "distance" : "-rating",
      }),
      reviewsApi.publicList(branch.club.id),
      bookingsApi.availability(branch.id, initialDate, 60).catch(() => undefined),
      barbersApi.getBarbers({ branch_id: branch.id, club_id: branch.club.id }).catch(() => []),
    ])
    const barberItems = Array.isArray(barbersRes) ? barbersRes : ((barbersRes as any)?.results || [])
    return {
      branch,
      related: related.results.filter(item => item.id !== branch.id).slice(0, 6),
      reviews: reviews.results,
      initialAvail,
      barbers: barberItems,
    }
  },
)

const branch = computed(() => data.value?.branch)
const barbers = computed(() => data.value?.barbers ?? [])
const nearbyBranches = computed(() => data.value?.related ?? [])
const reviews = computed(() => data.value?.reviews ?? [])
const displayImages = computed(() => {
  if (!branch.value) return []
  const imgs = branch.value.images.map(img => img.image).filter(Boolean)
  const cover = branch.value.images.find(img => img.is_cover)?.image
  if (cover) {
    return [cover, ...imgs.filter(img => img !== cover)]
  }
  return imgs
})
const coverImage = computed(() => displayImages.value[0] || null)

const formatPrice = (value: number | null) => {
  if (value === null) return t("common.free")
  return `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`
}

const formatZonePrice = (value: number, bookingType: string) => {
  const suffix = bookingType === "PER_ZONE" ? t("branches.per_zone_suffix") : t("branches.per_seat_suffix")
  return `${new Intl.NumberFormat(locale.value).format(value / 100)} ${suffix}`
}

const serviceIcon = (type: string) => type === "PLAYSTATION" ? faGamepad : faComputer
const serviceName = (type: string) => t(type === "PLAYSTATION" ? "clubs.service_playstation" : "clubs.service_pc")

const selectedZoneId = ref("")
const bookingDate = ref("")
const durationHours = ref(1)
const selectedStartStartsAt = ref("")
const availability = ref<Awaited<ReturnType<typeof bookingsApi.availability>> | undefined>(data.value?.initialAvail)
const quantity = ref(1)
const availabilityLoading = ref(false)
const submitting = ref(false)
const bookingResult = ref<Booking>()
const bookingError = ref("")
let availabilityRequest = 0

const formatDuration = (minutes: number) => {
  if (!minutes) return t("bookings.duration_hours", { hours: 0 })
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  if (!hours) return t("branches.duration_minutes", { minutes: remainder })
  return remainder
    ? t("bookings.duration_hours_minutes", { hours, minutes: remainder })
    : t("bookings.duration_hours", { hours })
}

watch(branch, (value) => {
  if (!value) return
  bookingDate.value = dateInTimezone(value.timezone)
  if (value.zones && value.zones.length > 0 && !selectedZoneId.value) {
    selectedZoneId.value = value.zones[0]?.id || ""
  }
  if (data.value?.initialAvail) {
    availability.value = data.value.initialAvail
  }
}, { immediate: true })

const selectedZone = computed(() =>
  branch.value?.zones.find(zone => zone.id === selectedZoneId.value),
)
const selectedZoneAvailability = computed(() =>
  availability.value?.zones.find(zone => zone.id === selectedZoneId.value),
)

const minimumDate = computed(() => branch.value ? dateInTimezone(branch.value.timezone) : "")
const maximumDate = computed(() => branch.value && minimumDate.value
  ? addDays(minimumDate.value, branch.value.advance_booking_days)
  : "")

// Hourly clean slots calculation (Whole hour intervals 00:00, 01:00 ... 23:00)
const hourlyCleanSlots = computed(() => {
  if (!selectedZoneAvailability.value) return []
  const allSlots = selectedZoneAvailability.value.slots
  const mapped = allSlots.map((slot) => {
    const d = new Date(slot.starts_at)
    const formatter = new Intl.DateTimeFormat(locale.value, {
      timeZone: branch.value?.timezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })
    return {
      ...slot,
      timeLabel: formatter.format(d),
    }
  })
  // Filter whole hour slots (ends with :00) if multiple exist, else use all
  const wholeHours = mapped.filter(s => s.timeLabel.endsWith(":00"))
  return wholeHours.length > 0 ? wholeHours : mapped
})

const availableStartSlots = computed(() =>
  hourlyCleanSlots.value.filter(s => s.available > 0),
)

const selectedStartSlot = computed(() => {
  if (!selectedStartStartsAt.value) {
    return availableStartSlots.value[0] || null
  }
  return hourlyCleanSlots.value.find(s => s.starts_at === selectedStartStartsAt.value) || null
})

// Auto-select first available slot if not selected
watch(availableStartSlots, (slots) => {
  if (slots.length > 0 && !selectedStartStartsAt.value) {
    selectedStartStartsAt.value = slots[0]?.starts_at || ""
  }
}, { immediate: true })

const durationHourOptions = computed(() => {
  if (!selectedStartSlot.value) return []
  const startTime = new Date(selectedStartSlot.value.starts_at).getTime()
  const options = []
  for (let h = 1; h <= 5; h++) {
    const endD = new Date(startTime + h * 60 * 60 * 1000)
    const formatter = new Intl.DateTimeFormat(locale.value, {
      timeZone: branch.value?.timezone,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })
    options.push({
      hours: h,
      endTimeLabel: formatter.format(endD),
    })
  }
  return options
})

const selectedEndTimestamp = computed(() => {
  if (!selectedStartSlot.value) return null
  const startTime = new Date(selectedStartSlot.value.starts_at).getTime()
  return new Date(startTime + durationHours.value * 60 * 60 * 1000).toISOString()
})

const selectedEndTimeLabel = computed(() => {
  const opt = durationHourOptions.value.find(o => o.hours === durationHours.value)
  return opt ? opt.endTimeLabel : ""
})

const isSlotInRange = (slot: { starts_at: string }) => {
  if (!selectedStartSlot.value || !selectedEndTimestamp.value) return false
  const slotTime = new Date(slot.starts_at).getTime()
  const startTime = new Date(selectedStartSlot.value.starts_at).getTime()
  const endTime = new Date(selectedEndTimestamp.value).getTime()
  return slotTime >= startTime && slotTime < endTime
}

const isSlotStart = (slot: { starts_at: string }) => {
  return selectedStartSlot.value?.starts_at === slot.starts_at
}

const isSlotEnd = (slot: { starts_at: string }) => {
  if (!selectedStartSlot.value) return false
  const slotTime = new Date(slot.starts_at).getTime()
  const endTime = new Date(selectedStartSlot.value.starts_at).getTime() + (durationHours.value - 1) * 60 * 60 * 1000
  return slotTime === endTime
}

const onHourClick = (slot: { starts_at: string, available: number }) => {
  if (!slot.available) return
  if (!selectedStartStartsAt.value || durationHours.value > 1) {
    selectedStartStartsAt.value = slot.starts_at
    durationHours.value = 1
    return
  }
  const clickedTime = new Date(slot.starts_at).getTime()
  const startTime = new Date(selectedStartSlot.value!.starts_at).getTime()
  if (clickedTime > startTime) {
    const diffHours = Math.round((clickedTime - startTime) / (60 * 60 * 1000)) + 1
    durationHours.value = Math.min(diffHours, 5)
  } else {
    selectedStartStartsAt.value = slot.starts_at
    durationHours.value = 1
  }
}

const maximumQuantity = computed(() => selectedStartSlot.value?.available ?? 1)
const totalPrice = computed(() => {
  if (!selectedZone.value) return 0
  return Math.ceil(
    selectedZone.value.price_per_hour_tiyin
    * durationHours.value
    * quantity.value,
  )
})

const formatMoney = (value: number) =>
  `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`

const formatReviewDate = (value: string) => new Intl.DateTimeFormat(locale.value, {
  day: "2-digit",
  month: "short",
  year: "numeric",
}).format(new Date(value))

const loadAvailability = async () => {
  if (!branch.value || !selectedZoneId.value || !bookingDate.value) return
  const request = ++availabilityRequest
  availabilityLoading.value = true
  bookingError.value = ""
  quantity.value = 1
  try {
    const response = await bookingsApi.availability(
      branch.value.id,
      bookingDate.value,
      60, // Request 1-hour slots
    )
    if (request === availabilityRequest) availability.value = response
  } catch (error) {
    if (request === availabilityRequest) {
      bookingError.value = error instanceof ApiRequestError ? error.message : t("common.backend_unavailable")
    }
  } finally {
    if (request === availabilityRequest) availabilityLoading.value = false
  }
}

const selectZone = (zoneId: string) => {
  selectedZoneId.value = zoneId
  bookingResult.value = undefined
  void loadAvailability()
}

watch([bookingDate, selectedZoneId], () => {
  if (selectedZoneId.value) void loadAvailability()
})

const showAuthModal = ref(false)
const showContactModal = ref(false)

const handleBookingSubmit = async () => {
  if (!auth.isAuthenticated.value) {
    showAuthModal.value = true
    return
  }
  if (!auth.user.value?.phone) {
    showContactModal.value = true
    return
  }
  await submitBooking()
}

const onAuthenticated = async () => {
  if (!auth.user.value?.phone) {
    showContactModal.value = true
    return
  }
  await submitBooking()
}

const onContactSaved = async () => {
  await submitBooking()
}

const submitBooking = async () => {
  if (
    !selectedZone.value
    || !selectedStartSlot.value
    || !selectedEndTimestamp.value
    || submitting.value
  ) return
  submitting.value = true
  bookingError.value = ""
  try {
    const hold = await bookingsApi.createHold({
      zone_id: selectedZone.value.id,
      starts_at: selectedStartSlot.value.starts_at,
      ends_at: selectedEndTimestamp.value,
      quantity: quantity.value,
    })
    bookingResult.value = await bookingsApi.create(hold.id)
  } catch (error) {
    bookingError.value = error instanceof ApiRequestError ? error.message : t("common.backend_unavailable")
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="branch-page-wrapper">
    <!-- Back to catalog button -->
    <div class="branch-top-nav">
      <NuxtLink class="detail-back-link" to="/">
        <FontAwesomeIcon :icon="faArrowLeft" />
        <span>{{ branch?.club?.category === 'BARBERSHOP' ? t("barbers.all_barbershops") : t("clubs.all_clubs") }}</span>
      </NuxtLink>
    </div>

    <!-- Loading & Error States -->
    <div v-if="status === 'pending'" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faGamepad" /></span>
      <p>{{ t("common.loading") }}</p>
    </div>
    <div v-else-if="error || !branch" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faStore" /></span>
      <p class="form-message">{{ error?.message || t("clubs.not_found") }}</p>
    </div>

    <template v-else>
      <!-- Top 5-Photo Mosaic Gallery Grid -->
      <section class="branch-gallery-section" :class="{ 'single-img': displayImages.length <= 1 }">
        <!-- 1. Left Large Cover Photo -->
        <div class="gallery-main-frame">
          <img
            v-if="displayImages[0]"
            :src="displayImages[0]"
            :alt="branch.name"
            class="gallery-cover-img"
          >
          <div v-else class="gallery-placeholder">
            <FontAwesomeIcon :icon="faStore" />
          </div>
        </div>

        <!-- 2-5. Right 2x2 Photos Grid (Max 4 photos) -->
        <div v-if="displayImages.length > 1" class="gallery-side-thumbs-grid">
          <div
            v-for="(img, idx) in displayImages.slice(1, 5)"
            :key="idx"
            class="gallery-thumb-item"
            :class="{ 'is-last-item': idx === Math.min(displayImages.length - 2, 3) }"
          >
            <img :src="img" :alt="`${branch.name} - ${idx + 2}`" class="gallery-thumb-img">
            <!-- Rasm va videolar badge button on last visible photo -->
            <div
              v-if="idx === Math.min(displayImages.length - 2, 3)"
              class="gallery-all-photos-badge"
            >
              <FontAwesomeIcon :icon="faImages" />
              <span>RASM VA VIDEOLAR</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Branch Header Row -->
      <header class="branch-info-header">
        <div class="branch-heading-left">
          <h1>{{ branch.name }}</h1>
          <p class="branch-address-line">
            <FontAwesomeIcon :icon="faLocationDot" class="loc-icon" />
            <span>{{ branch.full_address }}</span>
          </p>
        </div>

        <div class="branch-heading-right">
          <div class="branch-rating-badge">
            <FontAwesomeIcon :icon="faStar" class="gold-star" />
            <strong>{{ Number(branch.club.rating || 5.0).toFixed(1) }}</strong>
            <small>({{ branch.club.review_count || reviews.length }} sharhlar)</small>
          </div>
          <span v-if="branch.is_24_hours" class="badge-247">
            <FontAwesomeIcon :icon="faClock" />
            {{ t("branches.is_24_hours") }}
          </span>
        </div>
      </header>

      <!-- Main 2-Column Content Layout -->
      <div class="branch-main-grid">
        <!-- Left Column -->
        <main class="branch-left-content">
          <!-- Sartaroshlar (Sartaroshxonalar uchun) -->
          <section v-if="branch.club.category === 'BARBERSHOP' || barbers.length" class="detail-card-block">
            <div class="detail-block-header">
              <h2>{{ t("barbers.our_barbers") }}</h2>
              <span class="count-pill">{{ barbers.length }}</span>
            </div>
            <div v-if="!barbers.length" class="empty-barbers-note">
              <p>{{ t("barbers.no_barbers_in_branch") }}</p>
            </div>
            <div v-else class="barbers-branch-grid">
              <BarberCard
                v-for="b in barbers"
                :key="b.id"
                :barber="b"
                @book="openBarberModal"
              />
            </div>
          </section>

          <!-- 1. Zones / Rooms Selector (O'yin klublari uchun) -->
          <section v-if="branch.zones.length && branch.club.category !== 'BARBERSHOP'" class="detail-card-block">
            <div class="detail-block-header">
              <h2>{{ t("branches.zones_title") }}</h2>
              <span class="count-pill">{{ branch.zones.length }}</span>
            </div>
            <div class="zone-options-grid">
              <button
                v-for="zone in branch.zones"
                :key="zone.id"
                type="button"
                class="zone-option-card"
                :class="{ active: selectedZoneId === zone.id }"
                @click="selectZone(zone.id)"
              >
                <div class="zone-card-top">
                  <span class="zone-resource-badge">
                    <FontAwesomeIcon :icon="serviceIcon(zone.resource_type)" />
                    {{ serviceName(zone.resource_type) }}
                  </span>
                  <strong>{{ formatZonePrice(zone.price_per_hour_tiyin, zone.booking_type) }}</strong>
                </div>
                <h3>{{ zone.name }}</h3>
                <p class="zone-capacity">
                  <FontAwesomeIcon :icon="faUsers" />
                  {{ t(zone.booking_type === "PER_ZONE" ? "branches.room_capacity" : "branches.seats_capacity", { count: zone.capacity }) }}
                </p>
              </button>
            </div>
          </section>

          <!-- 2. Interactive Range Booking Form (Bron qilish) -->
          <section v-if="selectedZone" class="detail-card-block booking-block">
            <div class="detail-block-header">
              <h2>{{ t("branches.title") }} — {{ selectedZone.name }}</h2>
            </div>

            <!-- Booking Success Message -->
            <div v-if="bookingResult" class="booking-success-box">
              <FontAwesomeIcon :icon="faCircleCheck" class="success-icon" />
              <div>
                <h3>{{ t("branches.booking_success") }}</h3>
                <p>{{ t("bookings.booking_number") }}: <strong>{{ bookingResult.booking_number }}</strong></p>
                <NuxtLink to="/bookings" class="view-bookings-btn">
                  {{ t("bookings.view_my_bookings") }}
                </NuxtLink>
              </div>
            </div>

            <!-- Ultra-Clean & Compact Booking Form -->
            <form v-else class="booking-minimal-form" @submit.prevent="handleBookingSubmit">
              <div class="booking-trio-row">
                <!-- 1. Sana -->
                <div class="trio-col">
                  <label class="trio-label">
                    <FontAwesomeIcon :icon="faCalendarDays" />
                    <span>{{ t("bookings.date") }}:</span>
                  </label>
                  <input
                    v-model="bookingDate"
                    type="date"
                    :min="minimumDate"
                    :max="maximumDate"
                    class="trio-control"
                  >
                </div>

                <!-- 2. Boshlanish vaqti -->
                <div class="trio-col">
                  <label class="trio-label">
                    <FontAwesomeIcon :icon="faClock" />
                    <span>{{ t("bookings.start_hour") }}:</span>
                  </label>
                  <select
                    v-model="selectedStartStartsAt"
                    class="trio-control"
                    :disabled="availabilityLoading || !hourlyCleanSlots.length"
                  >
                    <option value="" disabled>{{ t("bookings.select_hour_placeholder") }}</option>
                    <option
                      v-for="h in availableStartSlots"
                      :key="h.starts_at"
                      :value="h.starts_at"
                    >
                      {{ h.timeLabel }} ({{ t("bookings.seats_quantity", { count: h.available }) }})
                    </option>
                  </select>
                </div>

                <!-- 3. Davomiyligi -->
                <div class="trio-col">
                  <label class="trio-label">
                    <FontAwesomeIcon :icon="faClock" />
                    <span>{{ t("bookings.duration") }}:</span>
                  </label>
                  <select
                    v-model="durationHours"
                    class="trio-control"
                    :disabled="!selectedStartSlot"
                  >
                    <option
                      v-for="hOption in durationHourOptions"
                      :key="hOption.hours"
                      :value="hOption.hours"
                    >
                      {{ t("bookings.duration_hours_until", { hours: hOption.hours, time: hOption.endTimeLabel }) }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- Quantity Selector (Only for PER_SEAT / Zallar) -->
              <div v-if="selectedStartSlot && selectedZone.booking_type === 'PER_SEAT'" class="quantity-compact-row">
                <span class="quantity-title">{{ t("branches.seats_count") }}</span>
                <div class="counter-box">
                  <button type="button" :disabled="quantity <= 1" class="counter-btn" @click="quantity--">−</button>
                  <span class="counter-val">{{ t("bookings.seats_quantity", { count: quantity }) }}</span>
                  <button type="button" :disabled="quantity >= maximumQuantity" class="counter-btn" @click="quantity++">+</button>
                </div>
              </div>

              <!-- Fixed Room Notice (For PER_ZONE / Xonalar) -->
              <div v-else-if="selectedStartSlot && selectedZone.booking_type === 'PER_ZONE'" class="room-notice-banner">
                <FontAwesomeIcon :icon="faCircleCheck" class="room-notice-icon" />
                <span>{{ t("bookings.entire_room_notice", { capacity: selectedZone.capacity }) }}</span>
              </div>

              <p v-if="bookingError" class="booking-error-alert" role="alert">{{ bookingError }}</p>
            </form>
          </section>

          <!-- 3. Customer Reviews (Mijozlar sharhlari) -->
          <section class="detail-card-block">
            <div class="detail-block-header">
              <div class="reviews-header-left">
                <h2>{{ t("reviews.title") }}</h2>
                <div class="rating-badge-pill">
                  <FontAwesomeIcon :icon="faStar" class="gold-star" />
                  <strong>{{ Number(branch.club.rating || 5.0).toFixed(1) }}</strong>
                </div>
              </div>
              <span class="count-pill">{{ reviews.length }}</span>
            </div>

            <div v-if="reviews.length" class="reviews-feed-list">
              <article v-for="rev in reviews" :key="rev.id" class="review-comment-card">
                <div class="review-card-head">
                  <div class="review-author-info">
                    <span class="author-avatar">{{ (rev.author || "F").charAt(0).toUpperCase() }}</span>
                    <strong>{{ rev.author }}</strong>
                  </div>
                  <time class="review-time">{{ formatReviewDate(rev.created_at) }}</time>
                </div>
                <div class="review-stars-row">
                  <FontAwesomeIcon
                    v-for="starIdx in 5"
                    :key="starIdx"
                    :icon="faStar"
                    :class="{ active: starIdx <= rev.rating }"
                    class="review-star-svg"
                  />
                </div>
                <p v-if="rev.comment" class="review-text-body">{{ rev.comment }}</p>
              </article>
            </div>
            <p v-else class="reviews-empty-state">{{ t("reviews.no_reviews") }}</p>
          </section>

          <!-- 4. Nearby Other Branches -->
          <section v-if="nearbyBranches.length" class="detail-card-block">
            <div class="detail-block-header">
              <h2>{{ branch.club.category === 'BARBERSHOP' ? t("barbers.other_nearby_barbershops") : t("clubs.other_nearby_clubs") }}</h2>
              <span class="count-pill">{{ nearbyBranches.length }}</span>
            </div>
            <div class="similar-branches-grid">
              <BranchCard
                v-for="other in nearbyBranches"
                :key="other.id"
                :branch="other"
              />
            </div>
          </section>
        </main>

        <!-- Right Column (Sticky Booking Checkout, Payment & Rules Cards) -->
        <aside class="branch-right-sidebar">
          <!-- 1A. Gaming Club: Checkout Card -->
          <div v-if="branch.club.category !== 'BARBERSHOP'" class="checkout-sticky-card">
            <h3 class="checkout-card-title">{{ t("bookings.booking_summary") }}</h3>

            <div v-if="selectedZone && selectedStartSlot" class="checkout-summary-body">
              <div class="checkout-detail-row">
                <span>{{ t("bookings.zone_room") }}:</span>
                <strong>{{ selectedZone.name }}</strong>
              </div>
              <div class="checkout-detail-row">
                <span>{{ t("bookings.date") }}:</span>
                <strong>{{ bookingDate }}</strong>
              </div>
              <div class="checkout-detail-row">
                <span>{{ t("bookings.start_time") }}:</span>
                <strong class="accent-text">{{ selectedStartSlot.timeLabel }}</strong>
              </div>
              <div class="checkout-detail-row">
                <span>{{ t("bookings.end_time") }}:</span>
                <strong>{{ selectedEndTimeLabel }}</strong>
              </div>
              <div class="checkout-detail-row">
                <span>{{ t("bookings.duration") }}:</span>
                <strong>{{ t("bookings.duration_hours", { hours: durationHours }) }}</strong>
              </div>
              <div class="checkout-detail-row">
                <span>{{ selectedZone.booking_type === 'PER_ZONE' ? t("bookings.booking_type") : t("bookings.seats_count") }}:</span>
                <strong>
                  {{ selectedZone.booking_type === 'PER_ZONE' ? t("bookings.entire_room_with_cap", { count: selectedZone.capacity }) : t("bookings.seats_quantity", { count: quantity }) }}
                </strong>
              </div>

              <div class="checkout-divider" />

              <div class="checkout-total-row">
                <span>{{ t("bookings.total_price") }}:</span>
                <strong class="checkout-total-price">{{ formatMoney(totalPrice) }}</strong>
              </div>

              <!-- Main Book Button -->
              <button
                type="button"
                class="checkout-submit-btn"
                :disabled="!selectedStartSlot || submitting"
                @click="handleBookingSubmit"
              >
                {{ t(submitting ? "bookings.in_progress" : "bookings.book_now") }}
              </button>
            </div>

            <div v-else class="checkout-unselected-state">
              <p>{{ t("bookings.select_zone_and_time_prompt") }}</p>
            </div>

            <!-- Accepted Payment Methods Logos (Single unified strip) -->
            <div class="payment-methods-block">
              <div class="payment-methods-title">
                <FontAwesomeIcon :icon="faCreditCard" />
                <span>{{ t("bookings.accepted_payment_methods") }}</span>
              </div>
              <div class="payment-unified-strip">
                <img src="/payments/payme.png" alt="Payme" class="pay-strip-img logo-payme" title="Payme">
                <span class="pay-strip-divider" />
                <img src="/payments/click.png" alt="Click" class="pay-strip-img logo-click" title="Click">
                <span class="pay-strip-divider" />
                <img src="/payments/uzcard.png" alt="Uzcard" class="pay-strip-img logo-uzcard" title="Uzcard">
                <span class="pay-strip-divider" />
                <img src="/payments/humo.png" alt="Humo" class="pay-strip-img logo-humo" title="Humo">
              </div>
            </div>
          </div>

          <!-- 1B. Barbershop: Quick Info & Rules Card -->
          <div v-else class="checkout-sticky-card barbershop-sidebar-guide">
            <h3 class="checkout-card-title">{{ t("barbers.booking_title") }}</h3>
            <div class="barbershop-sidebar-body">
              <p class="barber-count-note">
                {{ t("barbers.staff_count_note", { count: barbers.length }) }}
              </p>
              <div class="barber-guide-tip">
                {{ t("barbers.guide_tip") }}
              </div>
              <div class="barber-payment-note">
                {{ t("barbers.payment_note") }}
              </div>
            </div>
          </div>

          <!-- 2. Booking Rules (Bronlash qoidalari - Compact card directly under checkout) -->
          <div class="rules-compact-card">
            <h4 class="rules-compact-title">
              <FontAwesomeIcon :icon="faCalendarDays" />
              <span>{{ t("clubs.booking_rules") }}</span>
            </h4>
            <div class="rules-compact-list">
              <div class="rule-mini-item">
                <FontAwesomeIcon :icon="faClock" class="rule-mini-icon" />
                <div>
                  <small>{{ t("branches.min_duration") }}</small>
                  <strong>{{ formatDuration(branch.minimum_booking_minutes) }}</strong>
                </div>
              </div>
              <div class="rule-mini-item">
                <FontAwesomeIcon :icon="faClock" class="rule-mini-icon" />
                <div>
                  <small>{{ t("branches.max_duration") }}</small>
                  <strong>{{ formatDuration(Math.min(branch.maximum_booking_minutes || 300, 300)) }}</strong>
                </div>
              </div>
              <div class="rule-mini-item">
                <FontAwesomeIcon :icon="faCalendarDays" class="rule-mini-icon" />
                <div>
                  <small>{{ t("branches.advance_booking") }}</small>
                  <strong>{{ t("common.days_count", { days: branch.advance_booking_days }) }}</strong>
                </div>
              </div>
              <div class="rule-mini-item">
                <FontAwesomeIcon :icon="faCheck" class="rule-mini-icon" />
                <div>
                  <small>{{ t("branches.free_cancellation") }}</small>
                  <strong>{{ t("branches.free_cancellation_before", { minutes: branch.free_cancellation_minutes }) }}</strong>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </template>

    <!-- Modals -->
    <TelegramAuthModal v-model="showAuthModal" @authenticated="onAuthenticated" />
    <TelegramContactModal v-model="showContactModal" @saved="onContactSaved" />
    <BarberBookingModal v-model="showBarberModal" :barber="selectedBarber" />
  </div>
</template>

<style scoped>
.branch-page-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  padding: 10px 0 60px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.barbers-branch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
  gap: 14px;
}

.similar-branches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
  gap: 14px;
}

.empty-barbers-note {
  padding: 24px;
  text-align: center;
  background: var(--surface);
  border-radius: 12px;
  color: var(--muted);
  font-size: 14px;
}

.branch-top-nav {
  display: flex;
  align-items: center;
}

.detail-back-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  transition: color 0.15s ease;
}

.detail-back-link:hover {
  color: var(--accent);
}

/* 5-Photo Mosaic Gallery Section */
.branch-gallery-section {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 10px;
  height: 420px;
  border-radius: 20px;
  overflow: hidden;
}

.branch-gallery-section.single-img {
  grid-template-columns: 1fr;
}

.gallery-main-frame {
  position: relative;
  height: 100%;
  background: #0f172a;
  overflow: hidden;
}

.gallery-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.gallery-main-frame:hover .gallery-cover-img {
  transform: scale(1.02);
}

.gallery-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 48px;
  color: var(--muted);
  background: var(--surface);
}

.gallery-side-thumbs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  height: 100%;
}

.gallery-thumb-item {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: #0f172a;
}

.gallery-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}

.gallery-thumb-item:hover .gallery-thumb-img {
  transform: scale(1.03);
}

.gallery-all-photos-badge {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  color: #ffffff;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.03em;
  border: 1px solid rgba(255, 255, 255, 0.2);
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* Header Section */
.branch-info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
  gap: 20px;
}

.branch-heading-left h1 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.01em;
}

.branch-address-line {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 6px;
}

.loc-icon {
  color: var(--accent);
}

.branch-heading-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.branch-rating-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 12px;
  background: color-mix(in srgb, #0284c7 15%, transparent);
  border: 1px solid color-mix(in srgb, #0284c7 35%, transparent);
  color: var(--text);
  font-size: 13px;
}

.gold-star {
  color: #facc15;
}

.badge-247 {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 12px;
  background: color-mix(in srgb, #10b981 15%, transparent);
  border: 1px solid color-mix(in srgb, #10b981 35%, transparent);
  color: #10b981;
  font-size: 12px;
  font-weight: 750;
}

/* Main 2-Column Grid */
.branch-main-grid {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 28px;
  align-items: start;
}

.branch-left-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}

.detail-card-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.detail-block-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
}

.count-pill {
  font-size: 11px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--control) 80%, transparent);
  color: var(--muted);
}

/* Zones Grid */
.zone-options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.zone-option-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.zone-option-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.zone-option-card.active {
  border-color: #10b981;
  background: color-mix(in srgb, #10b981 8%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, #10b981 30%, transparent);
}

.zone-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.zone-resource-badge {
  font-size: 11px;
  font-weight: 750;
  color: var(--accent);
  display: flex;
  align-items: center;
  gap: 5px;
}

.zone-option-card h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
}

.zone-capacity {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Ultra-Clean & Compact Booking Form */
.booking-minimal-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.booking-trio-row {
  display: grid;
  grid-template-columns: 1fr 1.1fr 1.2fr;
  gap: 12px;
}

.trio-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.trio-label {
  font-size: 12px;
  font-weight: 750;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 6px;
}

.trio-control {
  height: 44px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--control) 80%, transparent);
  color: var(--text);
  font-size: 13.5px;
  font-weight: 600;
  outline: 0;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  width: 100%;
}

.trio-control:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent);
}

.quantity-compact-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--control) 50%, transparent);
  border: 1px solid var(--border);
}

.room-notice-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 12px;
  background: color-mix(in srgb, #10b981 12%, transparent);
  border: 1px solid color-mix(in srgb, #10b981 30%, transparent);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.room-notice-icon {
  color: #10b981;
  font-size: 15px;
}

.quantity-title {
  font-size: 12.5px;
  font-weight: 750;
  color: var(--text);
}

.counter-box {
  display: flex;
  align-items: center;
  gap: 12px;
}

.counter-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}

.counter-val {
  font-size: 15px;
  font-weight: 800;
  min-width: 20px;
  text-align: center;
}

.booking-error-alert {
  margin: 0;
  font-size: 12.5px;
  color: #ef4444;
  font-weight: 700;
}

.booking-success-box {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 14px;
  background: color-mix(in srgb, #10b981 12%, transparent);
  border: 1px solid #10b981;
}

.success-icon {
  font-size: 36px;
  color: #10b981;
}

.view-bookings-btn {
  display: inline-block;
  margin-top: 8px;
  color: #10b981;
  font-size: 13px;
  font-weight: 750;
  text-decoration: underline;
}

/* Reviews Feed */
.reviews-feed-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.review-comment-card {
  padding: 16px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--control) 40%, transparent);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.review-author-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.author-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--accent-text);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 800;
}

.review-time {
  font-size: 11px;
  color: var(--muted);
}

.review-stars-row {
  display: flex;
  gap: 3px;
}

.review-star-svg {
  font-size: 11px;
  color: var(--border);
}

.review-star-svg.active {
  color: #facc15;
}

.review-text-body {
  margin: 0;
  font-size: 13px;
  color: var(--text);
  line-height: 1.45;
}

/* Similar Branches */
.similar-branches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

/* Right Sticky Sidebar */
.branch-right-sidebar {
  position: sticky;
  top: 90px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.checkout-sticky-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
}

.checkout-card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.checkout-summary-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.checkout-detail-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--muted);
}

.checkout-detail-row strong {
  color: var(--text);
}

.accent-text {
  color: #10b981 !important;
  font-weight: 800;
}

.checkout-divider {
  height: 1px;
  background: var(--border);
  margin: 6px 0;
}

.checkout-total-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.checkout-total-row span {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.checkout-total-price {
  font-size: 22px;
  font-weight: 850;
  color: var(--text);
  letter-spacing: -0.02em;
}

.checkout-submit-btn {
  height: 48px;
  border-radius: 14px;
  border: 0;
  background: #10b981;
  color: #ffffff;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.checkout-submit-btn:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
}

.checkout-submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.checkout-unselected-state p {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  text-align: center;
  padding: 10px 0;
}

/* Payment Methods Badges */
.payment-methods-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.payment-methods-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
}

.payment-unified-strip {
  display: flex;
  align-items: center;
  justify-content: space-evenly;
  height: 50px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid var(--border);
  padding: 6px 14px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.05);
  transition: all 0.15s ease;
  overflow: hidden;
}

.payment-unified-strip:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.pay-strip-img {
  max-height: 26px;
  object-fit: contain;
  transition: transform 0.15s ease;
}

.pay-strip-img.logo-payme {
  max-height: 32px;
  max-width: 86px;
  transform: scale(1.18);
}

.pay-strip-img.logo-click {
  max-height: 32px;
  max-width: 86px;
  transform: scale(1.22);
}

.pay-strip-img.logo-uzcard {
  max-height: 26px;
  max-width: 46px;
}

.pay-strip-img.logo-humo {
  max-height: 26px;
  max-width: 52px;
}

.pay-strip-divider {
  width: 1px;
  height: 22px;
  background: rgba(0, 0, 0, 0.1);
}

/* Compact Rules Card Under Checkout */
.rules-compact-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rules-compact-title {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.rules-compact-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.rule-mini-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.rule-mini-icon {
  font-size: 13px;
  color: var(--accent);
  margin-top: 2px;
}

.rule-mini-item small {
  display: block;
  font-size: 10.5px;
  color: var(--muted);
  line-height: 1.2;
}

.rule-mini-item strong {
  font-size: 12px;
  color: var(--text);
  font-weight: 750;
}

@media (max-width: 1024px) {
  .branch-main-grid {
    grid-template-columns: 1fr;
  }
  .branch-gallery-section {
    grid-template-columns: 1fr;
    height: 260px;
  }
  .gallery-side-thumbs-grid {
    display: none;
  }
  .branch-right-sidebar {
    position: static;
  }
  .time-range-selectors-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .branch-page-wrapper {
    gap: 16px;
    padding: 6px 0 40px;
  }

  .branch-gallery-section {
    height: 210px;
    border-radius: 14px;
  }

  .branch-header-hero {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .branch-title-main {
    font-size: 22px;
  }

  .branch-hero-meta {
    flex-wrap: wrap;
    gap: 8px;
  }

  .zone-options-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .booking-trio-row {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .barbers-branch-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .rules-compact-list {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .checkout-sticky-card {
    padding: 18px 14px;
    border-radius: 16px;
  }

  .payment-unified-strip {
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }
}
</style>
