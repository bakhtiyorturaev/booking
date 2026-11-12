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
const favorites = useFavorites()
const toast = useToast()

const isFavorite = computed(() => {
  const clubId = props.branch?.club?.id
  return Boolean(clubId && favorites.isFavorite(clubId))
})

const formatPrice = (value: number | null) => {
  if (props.branch?.club?.category === "BARBERSHOP") return "Kelishiladi"
  if (value === null || value === 0) return t("common.free")
  return `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`
}

const toggleFavorite = async (event: Event) => {
  event.preventDefault()
  event.stopPropagation()
  const targetId = props.branch?.club?.id
  if (targetId) {
    try { await favorites.toggle(targetId) }
    catch { toast.error(t("favorites.update_error")) }
  }
}

const displayAddress = computed(() => {
  if (props.branch?.address) return props.branch.address
  const city = props.branch?.city?.name || ""
  const full = props.branch?.full_address || ""
  if (city && full && full.startsWith(city)) {
    return full.slice(city.length).replace(/^[,\s]+/, "")
  }
  return full || props.branch?.address || ""
})

const ratingScore = computed(() => {
  const rating = Number(props.branch?.club?.rating || 0)
  return rating > 0 ? rating.toFixed(1) : "5.0"
})
</script>

<template>
  <!-- Rasm butun kartochkani egallaydi, ma'lumotlar rasm ustidagi qorong'i qatlamda. -->
  <article class="venue-card">
    <NuxtLink :to="`/branches/${branch.id}`" class="venue-link" :aria-label="branch.name">
      <img
        v-if="branch.cover_image"
        :src="branch.cover_image"
        alt=""
        class="venue-img"
        loading="lazy"
      >
      <span v-else class="venue-placeholder" aria-hidden="true"><FontAwesomeIcon :icon="faStore" /></span>
      <span class="venue-shade" aria-hidden="true" />

      <span class="venue-top">
        <span v-if="branch.distance_km !== null" class="venue-chip">{{ branch.distance_km.toFixed(1) }} km</span>
        <span v-if="branch.is_24_hours" class="venue-chip venue-chip-accent">24/7</span>
      </span>

      <span class="venue-body">
        <span class="venue-title-row">
          <img v-if="branch.logo" :src="branch.logo" alt="" class="venue-logo" loading="lazy">
          <span class="venue-title" :title="branch.name">{{ branch.name }}</span>
        </span>
        <span class="venue-meta">
          <FontAwesomeIcon :icon="faStar" class="venue-star" aria-hidden="true" />
          <strong>{{ ratingScore }}</strong>
          <span class="venue-sep" aria-hidden="true">·</span>
          <FontAwesomeIcon :icon="faLocationDot" class="venue-pin" aria-hidden="true" />
          <span class="venue-address" :title="branch.full_address">{{ displayAddress }}</span>
        </span>
        <span class="venue-bottom">
          <span v-if="branch.club?.category === 'BARBERSHOP'" class="venue-price"><strong>{{ t("barbers.barbershop") }}</strong></span>
          <span v-else class="venue-price">
            <strong>{{ formatPrice(branch.min_price_tiyin) }}</strong>
            <span>{{ t("clubs.per_hour_suffix") }}</span>
          </span>
          <span class="venue-cta">{{ branch.club?.category === 'BARBERSHOP' ? t("barbers.view_barbers") : t("bookings.book_now") }}</span>
        </span>
      </span>
    </NuxtLink>

    <!-- Havola ichida tugma bo'lmasligi uchun "sevimli" tugmasi havoladan tashqarida turadi. -->
    <button
      type="button"
      class="venue-heart"
      :class="{ active: isFavorite }"
      :aria-pressed="isFavorite"
      :disabled="favorites.isPending(branch.club.id) || favorites.loading.value"
      aria-label="Sevimlilar"
      @click="toggleFavorite"
    >
      <FontAwesomeIcon :icon="faHeart" />
    </button>
  </article>
</template>

<style scoped>
.venue-card { position: relative; border-radius: 24px; overflow: hidden; background: #12121c; border: 1px solid var(--glass-border); box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22); transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease; }
.venue-card:hover { transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 60%, transparent); box-shadow: 0 22px 46px rgba(0, 0, 0, 0.32); }
.venue-link { position: relative; display: flex; flex-direction: column; justify-content: space-between; aspect-ratio: 4 / 5; min-height: 300px; padding: 14px; color: #fff; text-decoration: none; isolation: isolate; }
.venue-link:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; border-radius: 24px; }
.venue-img { position: absolute; inset: 0; z-index: -2; width: 100%; height: 100%; object-fit: cover; transition: transform .5s ease; }
.venue-card:hover .venue-img { transform: scale(1.05); }
.venue-placeholder { position: absolute; inset: 0; z-index: -2; display: grid; place-items: center; background: radial-gradient(circle at 30% 20%, #3b2f8f, #12121c 70%); color: rgba(255, 255, 255, 0.4); font-size: 40px; }
.venue-shade { position: absolute; inset: 0; z-index: -1; background: linear-gradient(180deg, rgba(7, 7, 13, 0.25) 0%, rgba(7, 7, 13, 0) 22%, rgba(7, 7, 13, 0.35) 48%, rgba(7, 7, 13, 0.94) 100%); }

.venue-top { display: flex; gap: 6px; padding-right: 48px; }
.venue-chip { display: inline-flex; align-items: center; min-height: 28px; padding: 0 11px; border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 999px; background: rgba(7, 7, 13, 0.55); color: #fff; font-size: 13px; font-weight: 800; -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); }
.venue-chip-accent { color: #c4bdff; }

.venue-body { display: flex; flex-direction: column; gap: 8px; }
.venue-title-row { display: flex; align-items: center; gap: 8px; min-width: 0; }
.venue-logo { width: 30px; height: 30px; flex-shrink: 0; border-radius: 9px; object-fit: cover; border: 1px solid rgba(255, 255, 255, 0.3); }
.venue-title { min-width: 0; overflow: hidden; font-family: var(--font-display); font-size: 18px; font-weight: 800; line-height: 1.2; letter-spacing: -0.01em; white-space: nowrap; text-overflow: ellipsis; }
.venue-meta { display: flex; align-items: center; gap: 5px; min-width: 0; color: rgba(255, 255, 255, 0.85); font-size: 14px; }
.venue-meta strong { color: #fff; }
.venue-star { color: #fbbf24; font-size: 13px; }
.venue-pin { flex-shrink: 0; font-size: 12px; color: rgba(255, 255, 255, 0.7); }
.venue-address { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.venue-bottom { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 4px; }
.venue-price { display: flex; flex-direction: column; min-width: 0; line-height: 1.2; }
.venue-price strong { font-size: 16px; font-weight: 800; white-space: nowrap; }
.venue-price span { color: rgba(255, 255, 255, 0.75); font-size: 13px; font-weight: 600; }
.venue-cta { flex-shrink: 0; display: inline-flex; align-items: center; min-height: 42px; padding: 0 16px; border-radius: 14px; background: var(--cta); color: #fff; font-size: 14px; font-weight: 800; box-shadow: 0 8px 22px rgba(109, 77, 255, 0.45); }

.venue-heart { position: absolute; top: 12px; right: 12px; z-index: 2; display: grid; place-items: center; width: 40px; height: 40px; padding: 0; border: 1px solid rgba(255, 255, 255, 0.24); border-radius: 50%; background: rgba(7, 7, 13, 0.55); color: #fff; font-size: 16px; cursor: pointer; -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); transition: transform .15s ease, background .15s ease; }
.venue-heart:hover { transform: scale(1.08); }
.venue-heart.active { background: #fff; color: #ef4444; }
.venue-heart:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }
.venue-heart:disabled { cursor: wait; }

@media (max-width: 640px) {
  .venue-link { aspect-ratio: 16 / 13; min-height: 260px; padding: 14px; }
}
@media (prefers-reduced-motion: reduce) {
  .venue-card, .venue-img, .venue-heart { transition: none; }
  .venue-card:hover, .venue-card:hover .venue-img { transform: none; }
}
</style>
