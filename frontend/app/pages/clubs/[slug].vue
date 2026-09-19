<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faArrowLeft,
  faCircleCheck,
  faClock,
  faGamepad,
  faLocationDot,
  faStar,
  faStore,
} from "@fortawesome/free-solid-svg-icons"

import { useClubsApi } from "~/api/clubs"

definePageMeta({ layout: "customer" })

const route = useRoute()
const clubsApi = useClubsApi()
const { locale, load, t } = useTranslations()
await load()
if (t("nav.back_to_clubs") === "nav.back_to_clubs") await load(locale.value, true)

const slug = computed(() => String(route.params.slug || ""))
const { data: club, error, status } = await useAsyncData(
  () => `club-${slug.value}`,
  () => clubsApi.get(slug.value),
)

useHead({
  title: computed(() => club.value?.name || t("clubs.title") || "Klub"),
})

const formatPrice = (value: number | null) => {
  if (value === null) return t("common.free")
  return `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`
}

const serviceName = (type: string) => t(type === "PLAYSTATION" ? "clubs.service_playstation" : "clubs.service_pc")
</script>

<template>
  <section class="club-detail-page">
    <NuxtLink class="detail-back-link" to="/">
      <FontAwesomeIcon :icon="faArrowLeft" />
      {{ t("nav.back_to_clubs") }}
    </NuxtLink>

    <div v-if="status === 'pending'" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faGamepad" /></span>
      <p>{{ t("common.loading") }}</p>
    </div>

    <div v-else-if="error || !club" class="catalog-empty">
      <span class="empty-icon"><FontAwesomeIcon :icon="faStore" /></span>
      <p class="form-message">{{ error?.message || t("clubs.not_found") }}</p>
    </div>

    <template v-else>
      <header class="club-detail-hero">
        <div class="club-detail-cover">
          <img v-if="club.cover" :src="club.cover" :alt="club.name">
          <FontAwesomeIcon v-else :icon="faGamepad" />
        </div>
        <div class="club-detail-heading">
          <div class="club-logo club-detail-logo">
            <img v-if="club.logo" :src="club.logo" alt="">
            <FontAwesomeIcon v-else :icon="faGamepad" />
          </div>
          <div>
            <h1>
              {{ club.name }}
              <FontAwesomeIcon
                v-if="club.is_verified"
                class="verified-icon"
                :icon="faCircleCheck"
                :aria-label="t('clubs.verified')"
              />
            </h1>
            <div class="club-rating">
              <FontAwesomeIcon :icon="faStar" />
              <strong>{{ club.rating }}</strong>
              <span>({{ club.review_count }})</span>
            </div>
          </div>
        </div>
      </header>

      <div class="detail-section-heading">
        <h2>{{ t("clubs.branches_title") }}</h2>
        <span>{{ club.branches.length }}</span>
      </div>

      <div v-if="club.branches.length" class="detail-branch-grid">
        <article v-for="branch in club.branches" :key="branch.id" class="detail-branch-card">
          <div class="detail-branch-image">
            <img v-if="branch.cover_image" :src="branch.cover_image" :alt="branch.name">
            <FontAwesomeIcon v-else :icon="faStore" />
          </div>
          <div class="detail-branch-body">
            <div class="detail-branch-title">
              <h3>{{ branch.name }}</h3>
              <strong>{{ formatPrice(branch.min_price_tiyin) }}</strong>
            </div>
            <p><FontAwesomeIcon :icon="faLocationDot" />{{ branch.full_address }}</p>
            <div class="branch-tags">
              <span v-if="branch.is_24_hours">
                <FontAwesomeIcon :icon="faClock" />{{ t("branches.is_24_hours") }}
              </span>
              <span v-for="service in branch.service_types" :key="service">
                {{ serviceName(service) }}
              </span>
            </div>
          </div>
        </article>
      </div>
      <div v-else class="catalog-empty compact-empty">
        <p>{{ t("clubs.no_branches") }}</p>
      </div>
    </template>
  </section>
</template>
