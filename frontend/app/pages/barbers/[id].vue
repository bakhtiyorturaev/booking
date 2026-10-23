<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faArrowLeft,
  faClock,
  faGamepad,
  faLocationDot,
  faPhone,
  faStar,
  faStore,
  faUser,
} from "@fortawesome/free-solid-svg-icons"
import { useBarbersApi } from "~/api/barbers"
import BarberBookingModal from "~/components/catalog/BarberBookingModal.vue"
import type { BarberItem } from "~/types/barber"

definePageMeta({ layout: "customer" })

const route = useRoute()
const router = useRouter()
const barbersApi = useBarbersApi()
const { t } = useTranslations()

const id = computed(() => String(route.params.id || ""))

const { data: barber, error, status } = await useAsyncData<BarberItem>(
  () => `barber-${id.value}`,
  () => barbersApi.getBarber(id.value),
)

const showBookingModal = ref(false)
const openBooking = () => { showBookingModal.value = true }

const goBack = () => {
  if (window.history.length > 1) router.back()
  else router.push("/catalog")
}

const ratingScore = computed(() => {
  const rating = Number(barber.value?.rating || 0)
  return rating > 0 ? rating.toFixed(1) : "5.0"
})

const getStatusDisplay = (status: string) => {
  switch (status) {
    case "AVAILABLE": return t("barbers.status_available")
    case "BREAK": return t("barbers.status_break")
    case "NOT_AT_WORK": return t("barbers.status_not_at_work")
    case "DAY_OFF": return t("barbers.status_day_off")
    default: return status
  }
}

const branchFullAddress = computed(() => {
  const b = barber.value
  if (!b) return ""
  const parts = [b.branch_address, b.branch_district, b.branch_city].filter(Boolean)
  return parts.length ? parts.join(", ") : ""
})

const weekdayLabels = computed(() => [1, 2, 3, 4, 5, 6, 7].map(day => ({ day, label: t(`barbers.day_${day}`) })))
</script>

<template>
  <div class="barber-page-wrapper">
    <div class="barber-top-nav">
      <button type="button" class="detail-back-link" @click="goBack">
        <FontAwesomeIcon :icon="faArrowLeft" />
        <span>{{ t("common.back") }}</span>
      </button>
    </div>

    <div v-if="status === 'pending'" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faGamepad" /></span>
      <p>{{ t("common.loading") }}</p>
    </div>
    <div v-else-if="error || !barber" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faUser" /></span>
      <p>{{ error?.message || t("clubs.not_found") }}</p>
    </div>

    <template v-else>
      <div class="barber-hero">
        <img v-if="barber.photo" :src="barber.photo" :alt="barber.full_name" class="barber-hero-img">
        <div v-else class="barber-hero-placeholder">
          <FontAwesomeIcon :icon="faUser" />
        </div>
      </div>

      <header class="barber-profile-header">
        <div class="barber-heading-left">
          <h1>{{ barber.full_name }}</h1>
          <div class="status-indicator">
            <span class="dot" :class="barber.status.toLowerCase()" />
            <span>{{ getStatusDisplay(barber.status) }}</span>
          </div>
        </div>
        <div class="barber-rating-badge">
          <FontAwesomeIcon :icon="faStar" class="gold-star" />
          <strong>{{ ratingScore }}</strong>
          <small>({{ barber.review_count }} {{ t('reviews.title').toLowerCase() }})</small>
        </div>
      </header>

      <section class="barber-info-card">
        <div class="info-row">
          <FontAwesomeIcon :icon="faStore" class="info-icon" />
          <div class="info-text">
            <span class="info-label">{{ t('barbers.venue') }}</span>
            <span class="info-value">{{ barber.club_name || t('barbers.barbershop') }}</span>
          </div>
        </div>

        <div v-if="barber.branch_name || branchFullAddress" class="info-row">
          <FontAwesomeIcon :icon="faLocationDot" class="info-icon" />
          <div class="info-text">
            <span class="info-label">{{ t('barbers.branch') }}</span>
            <span class="info-value">{{ barber.branch_name || t('barbers.main_branch') }}</span>
            <span v-if="branchFullAddress" class="info-subvalue">{{ branchFullAddress }}</span>
            <span v-if="barber.distance_km !== null && barber.distance_km !== undefined" class="info-subvalue">
              {{ t('barbers.distance_km', { km: barber.distance_km.toFixed(1) }) }}
            </span>
          </div>
        </div>

        <div v-if="barber.phone" class="info-row">
          <FontAwesomeIcon :icon="faPhone" class="info-icon" />
          <div class="info-text">
            <span class="info-label">{{ t('auth.phone_number') }}</span>
            <a :href="`tel:${barber.phone}`" class="info-value info-link">{{ barber.phone }}</a>
          </div>
        </div>

        <div class="info-row">
          <FontAwesomeIcon :icon="faClock" class="info-icon" />
          <div class="info-text">
            <span class="info-label">{{ t('barbers.work_time') }}</span>
            <span class="info-value">
              {{ (barber.work_start_time || '09:00').slice(0, 5) }} - {{ (barber.work_end_time || '20:00').slice(0, 5) }}
            </span>
            <div class="weekday-chips">
              <span
                v-for="wd in weekdayLabels"
                :key="wd.day"
                class="weekday-chip"
                :class="{ active: barber.working_days?.includes(wd.day) }"
              >
                {{ wd.label }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <button
        type="button"
        class="barber-book-cta"
        :class="{ 'is-disabled': barber.status === 'DAY_OFF' }"
        :disabled="barber.status === 'DAY_OFF'"
        @click="openBooking"
      >
        {{ barber.status === 'DAY_OFF' ? t('barbers.day_off_today') : t('bookings.book_now') }}
      </button>
    </template>

    <BarberBookingModal v-model="showBookingModal" :barber="barber ?? null" />
  </div>
</template>

<style scoped>
.barber-page-wrapper {
  max-width: 640px;
  margin: 0 auto;
  padding: 10px 0 60px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.barber-top-nav .detail-back-link {
  background: none;
  border: 0;
  cursor: pointer;
  margin-bottom: 0;
  font: inherit;
}

.barber-hero {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid var(--panel-border);
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
}

.barber-hero-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.barber-hero-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 4.5rem;
  color: rgba(255, 255, 255, 0.25);
}

.barber-profile-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.barber-heading-left h1 {
  margin: 0 0 6px;
  font-size: 1.5rem;
  letter-spacing: -0.02em;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 0.85rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.available { background: #22c55e; }
.dot.break { background: #eab308; }
.dot.not_at_work { background: #f97316; }
.dot.day_off { background: #ef4444; }

.barber-rating-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface) 78%, transparent);
  border: 1px solid var(--panel-border);
  white-space: nowrap;
  flex-shrink: 0;
}

.gold-star {
  color: #facc15;
  font-size: 0.85rem;
}

.barber-rating-badge small {
  color: var(--muted);
  font-size: 0.78rem;
}

.barber-info-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
  border: 1px solid var(--panel-border);
  border-radius: 18px;
  background: var(--surface);
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.info-icon {
  margin-top: 3px;
  width: 18px;
  text-align: center;
  color: var(--accent);
  font-size: 0.95rem;
  flex-shrink: 0;
}

.info-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.info-label {
  font-size: 0.72rem;
  color: var(--muted);
  font-weight: 650;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.info-value {
  font-size: 0.95rem;
  color: var(--text);
  font-weight: 650;
}

.info-link {
  text-decoration: none;
  color: var(--accent);
}

.info-subvalue {
  font-size: 0.82rem;
  color: var(--muted);
}

.weekday-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.weekday-chip {
  padding: 4px 9px;
  border-radius: 8px;
  font-size: 0.72rem;
  font-weight: 650;
  background: color-mix(in srgb, var(--surface) 60%, transparent);
  border: 1px solid var(--panel-border);
  color: var(--muted);
}

.weekday-chip.active {
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  border-color: var(--accent);
  color: var(--accent);
}

.barber-book-cta {
  width: 100%;
  height: 50px;
  border: 0;
  border-radius: 12px;
  background: #10b981;
  color: #ffffff;
  font-size: 1rem;
  font-weight: 750;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(16, 185, 129, 0.25);
  transition: all 0.15s ease;
}

.barber-book-cta:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
}

.barber-book-cta:disabled,
.barber-book-cta.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
  background: var(--border);
  color: var(--muted);
  box-shadow: none;
  transform: none;
}
</style>
