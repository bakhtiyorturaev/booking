<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faHeart,
  faLocationDot,
  faStar,
  faStore,
} from "@fortawesome/free-solid-svg-icons"
import type { BranchListSummary } from "~/types/club"
import { useTranslations } from "~/composables/useTranslations"

const props = defineProps<{
  branch: BranchListSummary
}>()

const { locale, t } = useTranslations()

const isFavorite = ref(false)

const formatPrice = (value: number | null) => {
  if (props.branch.club?.category === "BARBERSHOP") return "Kelishiladi"
  if (value === null || value === 0) return t("common.free")
  return `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`
}

const toggleFavorite = (event: Event) => {
  event.preventDefault()
  event.stopPropagation()
  isFavorite.value = !isFavorite.value
}

const locationLabel = computed(() => {
  if (props.branch.district?.name) return props.branch.district.name
  if (props.branch.city?.name) return props.branch.city.name
  return props.branch.full_address.split(",")[0] || ""
})

const displayAddress = computed(() => {
  if (props.branch.address) return props.branch.address
  const city = props.branch.city?.name || ""
  if (city && props.branch.full_address.startsWith(city)) {
    return props.branch.full_address.slice(city.length).replace(/^[,\s]+/, "")
  }
  return props.branch.full_address
})

const ratingScore = computed(() => {
  const rating = Number(props.branch.club.rating || 0)
  return rating > 0 ? rating.toFixed(1) : "5.0"
})
</script>

<template>
  <article class="bronla-card">
    <NuxtLink :to="`/branches/${branch.id}`" class="bronla-card-link">
      <!-- Media Header -->
      <div class="bronla-media-wrapper">
        <img
          v-if="branch.cover_image"
          :src="branch.cover_image"
          :alt="branch.name"
          class="bronla-cover-img"
          loading="lazy"
        >
        <div v-else class="bronla-placeholder-img">
          <FontAwesomeIcon :icon="faStore" />
        </div>

        <!-- Top Badges Overlay -->
        <div class="bronla-badges-row">
          <span v-if="locationLabel" class="bronla-badge location-badge">
            {{ locationLabel }}
          </span>
          <span v-if="branch.distance_km !== null" class="bronla-badge distance-badge">
            {{ branch.distance_km.toFixed(1) }} km
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

        <span v-if="branch.is_24_hours" class="bronla-badge-bottom">
          ⚡ 24/7
        </span>
      </div>

      <!-- Card Content Body -->
      <div class="bronla-card-body">
        <!-- Branch Title & Rating Badge -->
        <div class="bronla-header-line">
          <h3 class="bronla-club-title" :title="branch.name">
            {{ branch.name }}
          </h3>
          <div class="bronla-rating-pill">
            <FontAwesomeIcon :icon="faStar" class="star-icon" />
            <span class="rating-num">{{ ratingScore }}</span>
          </div>
        </div>

        <!-- Address -->
        <p class="bronla-address" :title="branch.full_address">
          <FontAwesomeIcon :icon="faLocationDot" class="address-icon" />
          <span>{{ displayAddress }}</span>
        </p>

        <!-- Price Section -->
        <div class="bronla-price-block">
          <div v-if="branch.club?.category === 'BARBERSHOP'" class="bronla-price-value">
            <strong>{{ t("barbers.barbershop") }}</strong>
          </div>
          <div v-else class="bronla-price-value">
            <strong>{{ formatPrice(branch.min_price_tiyin) }}</strong>
            <span class="bronla-price-unit">{{ t("clubs.per_hour_suffix") }}</span>
          </div>
        </div>

        <!-- Action Button -->
        <button type="button" class="bronla-book-button">
          {{ branch.club?.category === 'BARBERSHOP' ? t("barbers.view_barbers") : t("bookings.book_now") }}
        </button>
      </div>
    </NuxtLink>
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

.bronla-card-link {
  display: flex;
  flex-direction: column;
  height: 100%;
  text-decoration: none;
  color: inherit;
}

.bronla-media-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #000000;
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

.bronla-placeholder-img {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-size: 30px;
  color: var(--muted);
  background: color-mix(in srgb, var(--control) 80%, transparent);
}

.bronla-badges-row {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  gap: 5px;
  z-index: 2;
}

.bronla-badge {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.location-badge {
  background: rgba(15, 23, 42, 0.85);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.distance-badge {
  background: rgba(2, 132, 199, 0.9);
  color: #ffffff;
}

.bronla-badge-bottom {
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 9.5px;
  font-weight: 800;
  background: rgba(0, 0, 0, 0.75);
  color: #38bdf8;
  backdrop-filter: blur(6px);
  border: 1px solid rgba(56, 189, 248, 0.3);
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

.bronla-club-title {
  margin: 0;
  font-size: 13.5px;
  font-weight: 750;
  line-height: 1.3;
  color: var(--text);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
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

.bronla-address {
  margin: 0 0 8px;
  font-size: 11.5px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.address-icon {
  color: var(--accent);
  flex-shrink: 0;
  font-size: 11px;
}

.bronla-price-block {
  margin-top: auto;
  margin-bottom: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.bronla-price-value strong {
  font-size: 14.5px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.02em;
}

.bronla-price-unit {
  font-size: 11px;
  color: var(--muted);
  margin-left: 3px;
}

.bronla-book-button {
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

.bronla-book-button:hover {
  background: #059669;
  transform: translateY(-1px);
  box-shadow: 0 5px 15px rgba(16, 185, 129, 0.35);
}

@media (max-width: 640px) {
  .bronla-card {
    border-radius: 12px;
  }

  .bronla-card-body {
    padding: 8px 8px 10px;
  }

  .bronla-club-title {
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

  .bronla-address {
    font-size: 10px;
    margin-bottom: 6px;
    gap: 3px;
  }

  .address-icon {
    font-size: 9.5px;
  }

  .bronla-price-block {
    padding-top: 6px;
    margin-bottom: 8px;
  }

  .bronla-price-value strong {
    font-size: 12px;
  }

  .bronla-price-unit {
    font-size: 9.5px;
  }

  .bronla-book-button {
    height: 32px;
    font-size: 11.5px;
    font-weight: 700;
    border-radius: 8px;
    padding: 0 4px;
  }

  .bronla-badge {
    padding: 2px 5px;
    font-size: 8.5px;
    border-radius: 4px;
  }

  .bronla-heart-btn {
    width: 24px;
    height: 24px;
    font-size: 10px;
    top: 6px;
    right: 6px;
  }

  .bronla-badge-bottom {
    font-size: 8.5px;
    padding: 1px 4px;
    bottom: 6px;
    right: 6px;
  }
}
</style>
