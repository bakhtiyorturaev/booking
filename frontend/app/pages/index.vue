<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faArrowRight, faFire } from "@fortawesome/free-solid-svg-icons"
import { useBranchesApi } from "~/api/branches"
import { useServiceTypesApi, type ServiceTypeOption } from "~/api/serviceTypes"
import BranchCard from "~/components/catalog/BranchCard.vue"

definePageMeta({ layout: "customer" })

const TOP_LIMIT = 8

const branchesApi = useBranchesApi()
const serviceTypesApi = useServiceTypesApi()
const { locale, load, t } = useTranslations()
await load()

useHead({ title: computed(() => `${t("home.top_label")} — ${t("nav.home")}`) })

const { data: serviceTypeData } = await useAsyncData("public-service-types", () => serviceTypesApi.list())
const roots = computed<ServiceTypeOption[]>(() => Array.isArray(serviceTypeData.value)
  ? serviceTypeData.value
    .filter(service => !service.parent)
    .map(service => ({ ...service, name: service.translations?.[locale.value] || service.name }))
  : [])

type TopBranch = Awaited<ReturnType<typeof branchesApi.top>>[number]

const { data: topLists, status } = await useAsyncData("home-top-branches", async () => {
  const lists: Record<string, TopBranch[]> = {}
  await Promise.all(roots.value.map(async (service) => {
    try {
      const result = await branchesApi.top({ service_category: service.code, limit: TOP_LIMIT })
      lists[service.code] = Array.isArray(result) ? result : []
    } catch (error) {
      console.error("Fetch top branches error:", error)
      lists[service.code] = []
    }
  }))
  return lists
})

const sections = computed(() => roots.value
  .map(service => ({ service, branches: topLists.value?.[service.code] ?? [] }))
  .filter(section => section.branches.length))
</script>

<template>
  <div class="top-page">
    <header class="top-page-head">
      <h1><FontAwesomeIcon :icon="faFire" /> {{ t("home.top_label") }}</h1>
      <p>{{ t("home.top_subtitle") }}</p>
    </header>

    <div v-if="status === 'pending' && !sections.length" class="top-empty" aria-live="polite">Yuklanmoqda…</div>
    <div v-else-if="!sections.length" class="top-empty">{{ t("home.top_empty") }}</div>

    <section v-for="section in sections" :key="section.service.id" class="top-section" :aria-label="`${t('home.top_label')} ${section.service.name}`">
      <div class="top-section-head">
        <h2>{{ t("home.top_label") }} <span>{{ section.service.name }}</span></h2>
        <NuxtLink :to="{ path: '/catalog', query: { service: section.service.code } }" class="top-view-all">
          {{ t("home.top_view_all") }} <FontAwesomeIcon :icon="faArrowRight" />
        </NuxtLink>
      </div>
      <ol class="top-row">
        <li v-for="(branch, index) in section.branches" :key="branch.id" class="top-item">
          <span class="top-rank" :class="{ 'top-rank--lead': index < 3 }" aria-hidden="true">{{ index + 1 }}</span>
          <span v-if="branch.bookings_30d > 0" class="top-bookings">{{ t("home.top_bookings", { count: branch.bookings_30d }) }}</span>
          <BranchCard :branch="branch" />
        </li>
      </ol>
    </section>
  </div>
</template>

<style scoped>
.top-page { display: flex; flex-direction: column; gap: 22px; width: 100%; max-width: 1440px; margin: 0 auto; padding: 8px 0 40px; }
.top-page-head h1 { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 24px; font-weight: 850; color: var(--text); }
.top-page-head h1 svg { color: #f97316; }
.top-page-head p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
.top-empty { padding: 40px; border: 1px dashed var(--border); border-radius: 16px; background: var(--surface); color: var(--muted); text-align: center; }
.top-section { display: flex; flex-direction: column; gap: 10px; padding: 14px; border: 1px solid var(--panel-border); border-radius: 18px; background: color-mix(in srgb, var(--surface) 92%, transparent); backdrop-filter: blur(10px); }
.top-section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.top-section-head h2 { margin: 0; font-size: 17px; font-weight: 800; color: var(--text); }
.top-section-head h2 span { color: var(--accent); }
.top-view-all { display: inline-flex; align-items: center; gap: 6px; color: var(--accent); font-size: 13px; font-weight: 700; text-decoration: none; white-space: nowrap; }
.top-view-all:hover { text-decoration: underline; }
.top-row { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(215px, 235px); gap: 14px; margin: 0; padding: 4px 2px 10px; overflow-x: auto; list-style: none; scroll-snap-type: x proximity; scrollbar-width: thin; }
.top-item { position: relative; scroll-snap-align: start; min-width: 0; }
.top-rank { position: absolute; z-index: 2; top: 8px; left: 8px; display: grid; place-items: center; min-width: 28px; height: 28px; padding: 0 6px; border-radius: 8px; background: rgba(15, 23, 42, 0.78); color: #fff; font-size: 13px; font-weight: 850; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
.top-rank--lead { background: linear-gradient(135deg, #f59e0b, #f97316); }
.top-bookings { position: absolute; z-index: 2; top: 8px; right: 48px; padding: 4px 8px; border-radius: 8px; background: rgba(15, 23, 42, 0.78); color: #fff; font-size: 11px; font-weight: 700; }
@media (max-width: 640px) {
  .top-page { gap: 16px; padding-top: 4px; }
  .top-page-head h1 { font-size: 20px; }
  .top-section { padding: 10px; border-radius: 14px; }
  .top-row { grid-auto-columns: minmax(170px, 190px); gap: 10px; }
}
</style>
