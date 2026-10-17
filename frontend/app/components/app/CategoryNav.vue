<script setup lang="ts">
import { useServiceTypesApi, type ServiceTypeOption } from "~/api/serviceTypes"
import { useAdminApi } from "~/api/admin"
import { serviceTreeOptions } from "~/utils/serviceTree"

const props = defineProps<{ cabinet?: boolean }>()
const cabinetPath = useCabinetPath()
const adminApi = useAdminApi()

const emit = defineEmits<{ (event: "navigate"): void }>()
const route = useRoute()
const { locale } = useTranslations()
const serviceTypesApi = useServiceTypesApi()

// Katalog sahifasi bilan bir xil kalit: so'rov bir marta bajariladi.
const { data } = await useAsyncData(
  props.cabinet ? "cabinet-navigation-service-types" : "public-service-types",
  () => props.cabinet ? adminApi.getServiceTypes() : serviceTypesApi.list(),
)
const services = computed<ServiceTypeOption[]>(() => Array.isArray(data.value)
  ? data.value.map(service => ({ ...service, name: service.translations?.[locale.value] || (locale.value === "ru" && "name_ru" in service ? service.name_ru as string : locale.value === "en" && "name_en" in service ? service.name_en as string : "") || service.name }))
  : [])
const expanded = ref<Set<string>>(new Set())
const hasChildren = (id: string) => services.value.some(service => service.parent === id)
const toggle = (id: string) => {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}
const serviceRows = computed(() => serviceTreeOptions(services.value).filter(service => {
  const seen = new Set<string>([service.id])
  let parent = service.parent
  while (parent) {
    if (seen.has(parent) || !expanded.value.has(parent)) return false
    seen.add(parent)
    parent = services.value.find(item => item.id === parent)?.parent
  }
  return true
}))
const serviceTarget = (service: ServiceTypeOption) => props.cabinet
  ? { path: cabinetPath("/clubs"), query: { service_type: service.id } }
  : { path: "/catalog", query: { service: service.code } }
const activeCode = computed(() => {
  if (props.cabinet) return route.path === cabinetPath("/clubs")
    ? services.value.find(service => service.id === route.query.service_type)?.code ?? null : null
  if (route.path !== "/catalog" || route.query.all === "1") return null
  return typeof route.query.service === "string" ? route.query.service
    : services.value.find(service => service.code.toUpperCase() === "GAMING_CLUB")?.code ?? services.value[0]?.code ?? null
})
watch(activeCode, (code) => {
  const next = new Set(expanded.value)
  let service = services.value.find(item => item.code === code)
  const seen = new Set<string>()
  while (service?.parent && !seen.has(service.id)) {
    seen.add(service.id)
    next.add(service.parent)
    service = services.value.find(item => item.id === service?.parent)
  }
  expanded.value = next
}, { immediate: true })
</script>

<template>
  <div class="service-navigation">
    <nav class="category-list" aria-label="Xizmat turlari">
      <template v-for="service in serviceRows" :key="service.id">
        <div v-if="hasChildren(service.id)" class="category-parent-row" :style="{ paddingInlineStart: `${service.depth * 14}px` }">
          <NuxtLink
            :to="serviceTarget(service)"
            :class="{ active: activeCode === service.code }"
            :aria-current="activeCode === service.code ? 'page' : undefined"
            @click="emit('navigate')"
          >{{ service.name }}</NuxtLink>
          <button
            type="button"
            class="category-parent category-expand"
            :aria-label="service.name"
            :aria-expanded="expanded.has(service.id)"
            @click="toggle(service.id)"
          >
            <span class="category-chevron" :class="{ expanded: expanded.has(service.id) }" aria-hidden="true">⌄</span>
          </button>
        </div>
        <NuxtLink
          v-else
          :to="serviceTarget(service)"
          :class="{ active: activeCode === service.code }"
          :aria-current="activeCode === service.code ? 'page' : undefined"
          :style="{ paddingInlineStart: `${12 + service.depth * 14}px` }"
          @click="emit('navigate')"
        >
          {{ service.name }}
        </NuxtLink>
      </template>
    </nav>
  </div>
</template>

<style scoped>
.category-list { display: flex; flex-direction: column; gap: 2px; }
.category-list a, .category-parent { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; min-height: 44px; padding: 10px 12px; border: 0; border-radius: 10px; background: transparent; color: var(--text); font: inherit; font-size: 14px; font-weight: 650; text-align: start; text-decoration: none; cursor: pointer; }
.category-list a:hover, .category-parent:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.category-list a.active { background: color-mix(in srgb, var(--accent) 14%, transparent); color: var(--accent); }
.category-list a:focus-visible, .category-parent:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.category-parent-row { display: flex; align-items: center; min-width: 0; }
.category-parent-row > a { flex: 1; min-width: 0; }
.category-parent-row > .category-expand { justify-content: center; flex: 0 0 44px; width: 44px; padding: 10px; }
.category-chevron { transition: transform 0.2s; }
.category-chevron.expanded { transform: rotate(180deg); }
@media (prefers-reduced-motion: reduce) { .category-chevron { transition: none; } }
</style>
