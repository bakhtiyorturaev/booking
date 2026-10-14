<script setup lang="ts">
import { useServiceTypesApi, type ServiceTypeOption } from "~/api/serviceTypes"
import { rootService } from "~/utils/serviceTree"

const emit = defineEmits<{ (event: "navigate"): void }>()
const route = useRoute()
const { locale, t } = useTranslations()
const serviceTypesApi = useServiceTypesApi()

// Katalog sahifasi bilan bir xil kalit: so'rov bir marta bajariladi.
const { data } = await useAsyncData("public-service-types", () => serviceTypesApi.list())
const services = computed<ServiceTypeOption[]>(() => Array.isArray(data.value)
  ? data.value.map(service => ({ ...service, name: service.translations?.[locale.value] || service.name }))
  : [])
const roots = computed(() => services.value.filter(service => !service.parent))

const onCatalog = computed(() => route.path === "/catalog")
const showingAll = computed(() => onCatalog.value && route.query.all === "1")
const activeRootCode = computed(() => {
  if (!onCatalog.value) return null
  const code = typeof route.query.service === "string" ? route.query.service : null
  const current = services.value.find(service => service.code === code)
    ?? services.value.find(service => service.code.toUpperCase() === "GAMING_CLUB")
    ?? roots.value[0]
    ?? null
  return rootService(services.value, current)?.code ?? null
})
</script>

<template>
  <nav class="category-list" aria-label="Xizmat turlari">
    <NuxtLink
      v-for="service in roots"
      :key="service.id"
      :to="{ path: '/catalog', query: { service: service.code } }"
      :class="{ active: !showingAll && activeRootCode === service.code }"
      @click="emit('navigate')"
    >
      {{ service.name }}
    </NuxtLink>
    <NuxtLink
      v-if="roots.length"
      :to="{ path: '/catalog', query: { all: '1' } }"
      :class="{ active: showingAll }"
      @click="emit('navigate')"
    >
      {{ t("catalog.all") }}
    </NuxtLink>
  </nav>
</template>

<style scoped>
.category-list { display: flex; flex-direction: column; gap: 2px; }
.category-list a { display: block; padding: 10px 12px; border-radius: 10px; color: var(--text); font-size: 14px; font-weight: 650; text-decoration: none; }
.category-list a:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.category-list a.active { background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--accent); }
.category-list a:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
</style>
