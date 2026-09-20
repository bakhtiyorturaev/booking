<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faClock,
  faHeart,
  faLocationDot,
  faStar,
  faStore,
  faUser,
} from "@fortawesome/free-solid-svg-icons"
import type { BarberItem } from "~/types/barber"
import { useTranslations } from "~/composables/useTranslations"
import { useFavorites } from "~/composables/useFavorites"

const { t } = useTranslations()
const favorites = useFavorites()

const props = defineProps<{
  barber: BarberItem
}>()

const emit = defineEmits<{
  (e: "book", barber: BarberItem): void
}>()

const isFavorite = computed(() => {
  if (props.barber.club_id) return favorites.isFavorite(props.barber.club_id)
  return favorites.isFavorite(props.barber.id)
})

const toggleFavorite = (event: Event) => {
  event.preventDefault()
  event.stopPropagation()
  const targetId = props.barber.club_id || props.barber.id
  if (targetId) {
    favorites.toggle(targetId)
  }
}

const ratingScore = computed(() => {
  const rating = Number(props.barber.rating || 0)
  return rating > 0 ? rating.toFixed(1) : "5.0"
})

const getStatusClass = (status: string) => {
  switch (status) {
    case "AVAILABLE": return "status-available"
    case "BREAK": return "status-break"
    case "NOT_AT_WORK": return "status-not-at-work"
    case "DAY_OFF": return "status-day-off"
    default: return ""
  }
}

const getStatusDisplay = (status: string) => {
  switch (status) {
    case "AVAILABLE": return t("barbers.status_available")
    case "BREAK": return t("barbers.status_break")
    case "NOT_AT_WORK": return t("barbers.status_not_at_work")
    case "DAY_OFF": return t("barbers.status_day_off")
    default: return props.barber.status_display
  }
}

const displayLocation = computed(() => {
  let branchPart = ""
  if (props.barber.branch_name) {
    const parts = props.barber.branch_name.split(/[-—]/).map(s => s.trim())
    if (parts.length > 1) {
      branchPart = parts[parts.length - 1] || ""
    }
  }

  const city = (props.barber.branch_city || "")
    .replace(" viloyati", "")
    .replace(" shahri", "")
    .replace(" sh.", "")
    .trim()

  if (branchPart && city) {
    return `${branchPart}, ${city}`
  }
  if (branchPart) {
    return branchPart
  }
  if (props.barber.branch_district && city) {
    return `${props.barber.branch_district}, ${city}`
  }
  if (props.barber.branch_address) {
    const addrParts = props.barber.branch_address.split(",").map(s => s.trim())
    return addrParts.length > 1 ? addrParts.slice(1).join(", ") : props.barber.branch_address
  }
  return city || props.barber.club_name || t("barbers.barbershop")
})
</script>

<template>
  <article class="bronla-card barber-card">
    <!-- Media / Avatar Header -->
    <div class="bronla-media-wrapper barber-media">
      <img
        v-if="barber.photo"
        :src="barber.photo"
        :alt="barber.full_name"
        class="bronla-cover-img barber-img"
        loading="lazy"
      >
      <div v-else class="barber-no-photo-banner">
        <div class="banner-gradient-bg">
          <FontAwesomeIcon :icon="faUser" class="banner-bg-watermark" />
          <span class="banner-barber-fullname">{{ barber.full_name }}</span>
        </div>
      </div>

      <!-- Top Status Badge Overlay -->
      <div class="bronla-badges-row">
        <span class="status-pill" :class="getStatusClass(barber.status)">
          <span class="status-dot" />
          {{ getStatusDisplay(barber.status) }}
        </span>
        <span v-if="barber.distance_km !== null && barber.distance_km !== undefined" class="status-pill distance-pill">
          {{ barber.distance_km.toFixed(1) }} km
        </span>
      </div>

      <!-- Favorite Heart Button -->
      <button
        type="button"
        class="bronla-heart-btn"
        :class="{ active: isFavorite }"
        aria-label="Sevimlilar"
        @click="toggleFavorite"
      >
        <FontAwesomeIcon :icon="faHeart" />
      </button>
    </div>

    <!-- Card Body -->
    <div class="bronla-card-body">
      <!-- 1. Barber Full Name & Rating Pill -->
      <div class="bronla-header-line">
        <h3 class="bronla-barber-name" :title="barber.full_name">
          {{ barber.full_name }}
        </h3>
        <div class="bronla-rating-pill">
          <FontAwesomeIcon :icon="faStar" class="star-icon" />
          <span class="rating-num">{{ ratingScore }}</span>
        </div>
      </div>

      <!-- 2. Barbershop Salon Subtitle -->
      <div class="barber-salon-meta" :title="barber.club_name">
        <FontAwesomeIcon :icon="faStore" class="salon-icon" />
        <span class="salon-name-text">{{ barber.club_name || t("barbers.barbershop") }}</span>
      </div>

      <!-- 3. Location under Name/Salon -->
      <p class="barber-location-meta" :title="displayLocation">
        <FontAwesomeIcon :icon="faLocationDot" class="location-icon" />
        <span>{{ displayLocation }}</span>
      </p>

      <!-- 4. Work Hours -->
      <p class="barber-time-meta">
        <FontAwesomeIcon :icon="faClock" class="clock-icon" />
        <span>{{ t("barbers.work_time") }} <strong>{{ (barber.work_start_time || '09:00').slice(0, 5) }} - {{ (barber.work_end_time || '20:00').slice(0, 5) }}</strong></span>
      </p>

      <!-- 5. Action Button -->
      <button
        type="button"
        class="bronla-book-button barber-action-btn"
        :class="{ 'is-disabled': barber.status === 'DAY_OFF' }"
        :disabled="barber.status === 'DAY_OFF'"
        @click="emit('book', barber)"
      >
        {{ barber.status === 'DAY_OFF' ? t('barbers.day_off_today') : t('bookings.book_now') }}
      </button>
    </div>
  </article>
</template>

<style scoped>
.bronla-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  position: relative;
}

.bronla-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.16);
  border-color: var(--accent);
}

.bronla-media-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: color-mix(in srgb, var(--surface) 50%, #000);
}

.bronla-cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.35s ease;
}

.bronla-card:hover .bronla-cover-img {
  transform: scale(1.05);
}

.barber-no-photo-banner {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
  overflow: hidden;
  padding: 12px;
}

.banner-gradient-bg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.banner-bg-watermark {
  position: absolute;
  font-size: 68px;
  color: rgba(255, 255, 255, 0.08);
  pointer-events: none;
}

.banner-barber-fullname {
  position: relative;
  z-index: 1;
  color: #ffffff;
  font-size: 15px;
  font-weight: 800;
  text-align: center;
  letter-spacing: -0.01em;
  line-height: 1.3;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.45);
  max-width: 85%;
  word-break: break-word;
}

.bronla-badges-row {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  gap: 5px;
  z-index: 2;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 750;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-pill.status-available {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.status-pill.status-available .status-dot {
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.status-pill.status-break {
  background: rgba(234, 179, 8, 0.2);
  color: #facc15;
  border: 1px solid rgba(234, 179, 8, 0.4);
}
.status-pill.status-break .status-dot {
  background: #eab308;
  box-shadow: 0 0 6px #eab308;
}

.status-pill.status-not-at-work {
  background: rgba(249, 115, 22, 0.2);
  color: #fb923c;
  border: 1px solid rgba(249, 115, 22, 0.4);
}
.status-pill.status-not-at-work .status-dot {
  background: #f97316;
  box-shadow: 0 0 6px #f97316;
}

.status-pill.status-day-off {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.4);
}
.status-pill.status-day-off .status-dot {
  background: #ef4444;
  box-shadow: 0 0 6px #ef4444;
}

.status-pill.distance-pill {
  background: rgba(2, 132, 199, 0.9);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.bronla-heart-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.7);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #ffffff;
  display: grid;
  place-items: center;
  font-size: 12px;
  cursor: pointer;
  z-index: 2;
  transition: all 0.15s ease;
}

.bronla-heart-btn:hover {
  transform: scale(1.1);
  background: rgba(239, 68, 68, 0.9);
}

.bronla-heart-btn.active {
  color: #ef4444;
  background: #ffffff;
}

.bronla-card-body {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.bronla-header-line {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 4px;
}

.bronla-barber-name {
  margin: 0;
  font-size: 13.5px;
  font-weight: 750;
  line-height: 1.3;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em;
  flex: 1;
}

.bronla-rating-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2.5px 6px;
  border-radius: 6px;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  color: #ffffff;
  font-size: 10px;
  font-weight: 750;
  flex-shrink: 0;
}

.star-icon {
  color: #facc15;
  font-size: 9px;
}

.rating-num {
  font-weight: 800;
}

.barber-salon-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 3px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--accent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.salon-icon {
  font-size: 10.5px;
  flex-shrink: 0;
  opacity: 0.9;
}

.salon-name-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.barber-location-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0 0 3px;
  font-size: 11.5px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.location-icon {
  color: #38bdf8;
  flex-shrink: 0;
  font-size: 11px;
}

.barber-time-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0 0 12px;
  font-size: 11.5px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.barber-time-meta .clock-icon {
  color: var(--accent);
  font-size: 11px;
  flex-shrink: 0;
}

.barber-time-meta strong {
  color: var(--text);
  font-weight: 700;
}

.bronla-book-button {
  margin-top: auto;
  width: 100%;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: #10b981;
  color: #ffffff;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}

.bronla-book-button:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
  box-shadow: 0 5px 15px rgba(16, 185, 129, 0.35);
}

.bronla-book-button:disabled,
.bronla-book-button.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
  background: var(--border);
  color: var(--muted);
  box-shadow: none;
  transform: none;
}

@media (max-width: 640px) {
  .bronla-card {
    border-radius: 12px;
  }

  .bronla-card-body {
    padding: 8px 8px 10px;
  }

  .bronla-barber-name {
    font-size: 12.5px;
  }

  .bronla-rating-pill {
    padding: 2px 5px;
    font-size: 9px;
    border-radius: 4px;
    gap: 2px;
  }

  .star-icon {
    font-size: 8px;
  }

  .barber-salon-meta {
    font-size: 10px;
    margin-bottom: 2px;
    gap: 3px;
  }

  .salon-icon {
    font-size: 9px;
  }

  .barber-location-meta {
    font-size: 10px;
    margin-bottom: 2px;
    gap: 3px;
  }

  .location-icon {
    font-size: 9.5px;
  }

  .barber-time-meta {
    font-size: 9.5px;
    margin-bottom: 8px;
    gap: 3px;
  }

  .barber-time-meta .clock-icon {
    font-size: 9px;
  }

  .bronla-book-button {
    height: 32px;
    font-size: 11.5px;
    font-weight: 700;
    border-radius: 8px;
    padding: 0 4px;
  }

  .status-pill {
    padding: 2px 6px;
    font-size: 8.5px;
    gap: 3px;
  }

  .status-dot {
    width: 4.5px;
    height: 4.5px;
  }

  .bronla-heart-btn {
    width: 24px;
    height: 24px;
    font-size: 10px;
    top: 6px;
    right: 6px;
  }

  .banner-barber-fullname {
    font-size: 11.5px;
    line-height: 1.2;
  }

  .banner-bg-watermark {
    font-size: 42px;
  }
}
</style>
