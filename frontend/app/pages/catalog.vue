<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faScissors,
  faSliders,
  faStore,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"
import { useBranchesApi, type BranchListParams } from "~/api/branches"
import { useBarbersApi } from "~/api/barbers"
import { useServiceTypesApi, type ServiceTypeOption } from "~/api/serviceTypes"
import BranchCard from "~/components/catalog/BranchCard.vue"
import BarberCard from "~/components/catalog/BarberCard.vue"
import BarberBookingModal from "~/components/catalog/BarberBookingModal.vue"
import CatalogSidebarFilter, { type FilterState } from "~/components/catalog/CatalogSidebarFilter.vue"
import CatalogBottomSheet from "~/components/catalog/CatalogBottomSheet.vue"
import type { BarberItem } from "~/types/barber"
import { descendantServiceIds, serviceTreeOptions } from "~/utils/serviceTree"

definePageMeta({ layout: "customer" })

const branchesApi = useBranchesApi()
const barbersApi = useBarbersApi()
const serviceTypesApi = useServiceTypesApi()
const { locale, load, t } = useTranslations()
await load()

const { data: serviceTypeData } = await useAsyncData("public-service-types", () => serviceTypesApi.list())
const serviceTypes = computed<ServiceTypeOption[]>(() => Array.isArray(serviceTypeData.value)
  ? serviceTypeData.value.map(service => ({ ...service, name: service.translations?.[locale.value] || service.name }))
  : [])
const route = useRoute()
const router = useRouter()
const queryServiceCode = () => {
  const code = route.query.service
  return typeof code === "string" ? serviceTypes.value.find(service => service.code === code)?.code ?? null : null
}
const selectedServiceCode = ref<string | null>(
  queryServiceCode()
  ?? serviceTypes.value.find(service => service.code.toUpperCase() === "GAMING_CLUB")?.code
  ?? serviceTypes.value[0]?.code
  ?? null,
)
const activeService = computed(() => serviceTypes.value.find(service => service.code === selectedServiceCode.value) ?? null)
const serviceRows = computed(() => serviceTreeOptions(serviceTypes.value))
const serviceAncestors = computed(() => {
  const result: ServiceTypeOption[] = []
  let current = activeService.value
  const seen = new Set<string>()
  while (current && !seen.has(current.id)) {
    seen.add(current.id)
    result.unshift(current)
    current = serviceTypes.value.find(item => item.id === current?.parent) || null
  }
  return result
})

const filterState = ref<FilterState>({
  search: "",
  city: "",
  ordering: "",
  service_type: "",
  status: "",
})
const draftFilterState = ref<FilterState>({ ...filterState.value })
const effectiveService = computed(() => serviceTypes.value.find(service => service.code === (filterState.value.service_type || selectedServiceCode.value)) || null)
const isBarbershop = computed(() => ["BARBERSHOP", "BARBER"].includes(effectiveService.value?.code.toUpperCase() || ""))
const isBarberOnly = computed(() => effectiveService.value?.code.toUpperCase() === "BARBER")
const serviceFilterOptions = computed(() => {
  const ids = descendantServiceIds(serviceTypes.value, activeService.value ? [activeService.value.id] : [])
  return serviceTypes.value.filter(service => ids.has(service.id) && service.id !== activeService.value?.id)
})
useHead({ title: computed(() => effectiveService.value?.name || t("clubs.catalog_title") || "Xizmatlar") })

const userCoords = ref<{ latitude: number; longitude: number } | null>(null)
const locating = ref(false)
const isLoading = ref(false)
const mobileFilterOpen = ref(false)
const allServicesOpen = ref(false)
const { message, show: showMessage, clear: clearMessage } = useTimedMessage()

const barbers = ref<BarberItem[]>([])
const barberCount = ref(0)
const selectedBarberForBooking = ref<BarberItem | null>(null)
const showBookingModal = ref(false)
const barbersSubView = ref<"barbers" | "salons">("barbers")

function extractList<T>(res: unknown): T[] {
  if (!res) return []
  if (Array.isArray(res)) return res as T[]
  if (typeof res === "object") {
    const payload = res as { results?: unknown; data?: unknown }
    if (Array.isArray(payload.results)) return payload.results as T[]
    if (Array.isArray(payload.data)) return payload.data as T[]
  }
  return []
}

const fetchBranches = async () => {
  isLoading.value = true
  clearMessage()
  try {
    const params: BranchListParams = {
      service_category: filterState.value.service_type || selectedServiceCode.value || undefined,
      search: filterState.value.search || undefined,
      city: filterState.value.city || undefined,
      ordering: filterState.value.ordering || undefined,
    }
    if (filterState.value.ordering === "distance" && userCoords.value) {
      params.latitude = userCoords.value.latitude
      params.longitude = userCoords.value.longitude
    }
    const response = await branchesApi.list(params)
    data.value = response

    if (isBarbershop.value) {
      const barberParams: Parameters<typeof barbersApi.getBarbers>[0] = {
        search: filterState.value.search || undefined,
        city: filterState.value.city || undefined,
        status: filterState.value.status || undefined,
        ordering: filterState.value.ordering || undefined,
      }
      if (filterState.value.ordering === "distance" && userCoords.value) {
        barberParams.latitude = userCoords.value.latitude
        barberParams.longitude = userCoords.value.longitude
      }
      const barbersRes = await barbersApi.getBarbers(barberParams)
      barbers.value = extractList<BarberItem>(barbersRes)
      barberCount.value = barbers.value.length
    } else {
      barbers.value = []
      barberCount.value = 0
    }
  } catch (error: unknown) {
    console.error("Fetch catalog error:", error)
  } finally {
    isLoading.value = false
  }
}

const { data } = await useAsyncData("branch-catalog", () => {
  return branchesApi.list({ service_category: selectedServiceCode.value || undefined, ordering: "-rating" })
})

const { data: initialBarbers } = await useAsyncData("barbers-catalog", () => {
  return barbersApi.getBarbers({ ordering: "-rating" })
})

if (initialBarbers.value) {
  barbers.value = extractList<BarberItem>(initialBarbers.value)
  barberCount.value = barbers.value.length
}

const branches = computed(() => data.value?.results ?? [])
const totalCount = computed(() => {
  if (isBarbershop.value) {
    return isBarberOnly.value || barbersSubView.value === "barbers" ? barberCount.value : data.value?.count ?? branches.value.length
  }
  return data.value?.count ?? branches.value.length
})

const setService = (code: string) => {
  if (selectedServiceCode.value === code) {
    allServicesOpen.value = false
    return
  }
  void router.replace({ query: { service: code } })
  selectedServiceCode.value = code
  barbersSubView.value = "barbers"
  filterState.value = {
    ...filterState.value,
    service_type: "",
    status: "",
    ordering: ["BARBERSHOP", "BARBER"].includes(code.toUpperCase().replaceAll("-", "_")) && ["price", "-price"].includes(filterState.value.ordering)
      ? "-rating"
      : filterState.value.ordering,
  }
  allServicesOpen.value = false
}

// Header kategoriyalari /catalog?service=KOD orqali keladi; ?all=1 "barcha xizmatlar" oynasini ochadi.
watch(() => route.query.service, () => {
  const code = queryServiceCode()
  if (code && code !== selectedServiceCode.value) setService(code)
})
const openAllFromQuery = () => {
  if (route.query.all !== "1") return
  allServicesOpen.value = true
  void router.replace({ query: selectedServiceCode.value ? { service: selectedServiceCode.value } : {} })
}
watch(() => route.query.all, openAllFromQuery)
onMounted(openAllFromQuery)

watch(
  [filterState, selectedServiceCode],
  () => {
    if (isBarbershop.value && ["price", "-price"].includes(filterState.value.ordering)) {
      filterState.value = { ...filterState.value, ordering: "-rating" }
      return
    }
    if (!isBarbershop.value && filterState.value.status) {
      filterState.value = { ...filterState.value, status: "" }
      return
    }
    void fetchBranches()
  },
  { deep: true },
)

const openMobileFilters = () => {
  draftFilterState.value = { ...filterState.value }
  mobileFilterOpen.value = true
}

const clearMobileFilters = () => {
  draftFilterState.value = { search: "", city: "", ordering: filterState.value.ordering, service_type: "", status: "" }
}

const applyMobileFilters = () => {
  if (draftFilterState.value.ordering !== "distance") userCoords.value = null
  filterState.value = { ...draftFilterState.value }
  mobileFilterOpen.value = false
}

const resetDraftFilters = () => {
  userCoords.value = null
}

const draftMatchesApplied = computed(() => JSON.stringify(draftFilterState.value) === JSON.stringify(filterState.value))
const filterCount = computed(() => [
  filterState.value.search,
  filterState.value.city,
  filterState.value.service_type,
  filterState.value.status,
  filterState.value.min_rating,
  filterState.value.min_price_tiyin,
  filterState.value.max_price_tiyin,
].filter(value => value !== undefined && value !== null && value !== "").length)

const mobileSortOptions = computed(() => [
  { value: "-rating", label: t("filter.sort_rating") },
  { value: "distance", label: t("filter.sort_nearest") },
  ...(!isBarbershop.value ? [
    { value: "price", label: t("filter.sort_price_asc") },
    { value: "-price", label: t("filter.sort_price_desc") },
  ] : []),
])

const changeMobileSort = (event: Event) => {
  const value = (event.target as HTMLSelectElement).value
  if (value === "distance") locate()
  else filterState.value = { ...filterState.value, ordering: value }
}

const activeFilterChips = computed(() => {
  const chips: { key: keyof FilterState; label: string }[] = []
  if (filterState.value.search) chips.push({ key: "search", label: filterState.value.search })
  if (filterState.value.service_type) {
    const value = filterState.value.service_type
    const label = serviceTypes.value.find(service => service.code === value)?.name || value
    chips.push({ key: "service_type", label })
  }
  if (filterState.value.city) {
    const city = [
      ["Toshkent", "Toshkent shahri"], ["Toshkent viloyati", "Toshkent viloyati"],
      ["Samarqand", "Samarqand"], ["Buxoro", "Buxoro"], ["Farg'ona", "Farg‘ona"],
      ["Andijon", "Andijon"], ["Namangan", "Namangan"], ["Qashqadaryo", "Qashqadaryo"],
      ["Surxondaryo", "Surxondaryo"], ["Xorazm", "Xorazm"], ["Navoiy", "Navoiy"],
      ["Jizzax", "Jizzax"], ["Sirdaryo", "Sirdaryo"], ["Qoraqalpog'iston", "Qoraqalpog‘iston"],
    ].find(([id]) => id === filterState.value.city)
    chips.push({ key: "city", label: city?.[1] || filterState.value.city })
  }
  if (filterState.value.status) chips.push({ key: "status", label: filterState.value.status === "AVAILABLE" ? "Ishda" : "Tanaffusda" })
  if (filterState.value.ordering) {
    const labels: Record<string, string> = { distance: t("filter.sort_nearest"), "-rating": t("filter.sort_rating"), price: t("filter.sort_price_asc"), "-price": t("filter.sort_price_desc") }
    chips.push({ key: "ordering", label: labels[filterState.value.ordering] || filterState.value.ordering })
  }
  return chips
})

const removeFilter = (key: keyof FilterState) => {
  const next = { ...filterState.value }
  if (key === "min_rating" || key === "min_price_tiyin" || key === "max_price_tiyin") next[key] = undefined
  else next[key] = ""
  if (key === "ordering") userCoords.value = null
  filterState.value = next
}

const locate = () => {
  if (!navigator.geolocation || locating.value) return
  locating.value = true
  clearMessage()
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      userCoords.value = {
        latitude: coords.latitude,
        longitude: coords.longitude,
      }
      filterState.value.ordering = "distance"
      locating.value = false
    },
    () => {
      locating.value = false
      showMessage(t("clubs.not_found"))
    },
    { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 },
  )
}

const locateDraft = () => {
  if (!navigator.geolocation || locating.value) return
  locating.value = true
  navigator.geolocation.getCurrentPosition(
    ({ coords }) => {
      userCoords.value = { latitude: coords.latitude, longitude: coords.longitude }
      draftFilterState.value = { ...draftFilterState.value, ordering: "distance" }
      locating.value = false
    },
    () => {
      locating.value = false
      showMessage(t("clubs.not_found"))
    },
    { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 },
  )
}

const handleReset = () => {
  userCoords.value = null
}

const openBarberBooking = (barber: BarberItem) => {
  selectedBarberForBooking.value = barber
  showBookingModal.value = true
}

const openBarberInfo = (barber: BarberItem) => {
  navigateTo(`/barbers/${barber.id}`)
}
</script>

<template>
  <div class="bronla-portal-container">
    <div v-if="serviceAncestors.length > 1" class="service-breadcrumbs">
      <button v-for="service in serviceAncestors" :key="service.id" type="button" @click="setService(service.code)">{{ service.name }}</button>
    </div>

    <div v-if="activeFilterChips.length" class="active-filter-chips" aria-label="Tanlangan filtrlar">
      <button
        v-for="chip in activeFilterChips"
        :key="chip.key"
        type="button"
        class="active-filter-chip"
        :aria-label="`${chip.label} filtrini olib tashlash`"
        @click="removeFilter(chip.key)"
      >
        <span>{{ chip.label }}</span>
        <FontAwesomeIcon :icon="faXmark" aria-hidden="true" />
      </button>
    </div>

    <!-- Main 2-Column Content Layout -->
    <div class="portal-main-layout">
      <!-- Mobile Filter Toggle Button -->
      <div class="mobile-filter-bar">
        <button
          type="button"
          class="mobile-filter-trigger"
          aria-haspopup="dialog"
          :aria-expanded="mobileFilterOpen"
          @click="openMobileFilters"
        >
          <FontAwesomeIcon :icon="faSliders" />
          <span>{{ t("filter.title") || "Filtr" }}<template v-if="filterCount"> {{ filterCount }}</template></span>
        </button>
        <label class="mobile-sort-control">
          <span>{{ t("filter.sort_by") }}</span>
          <select class="mobile-sort-select" :value="filterState.ordering || '-rating'" :aria-label="t('filter.sort_by')" :disabled="locating" @change="changeMobileSort">
            <option v-for="option in mobileSortOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
      </div>

      <!-- Desktop sidebar -->
      <div class="portal-sidebar-wrapper">
        <CatalogSidebarFilter
          v-model="filterState"
          :category="effectiveService?.code || ''"
          :service-options="serviceFilterOptions"
          :sub-view="barbersSubView"
          :locating="locating"
          @locate="locate"
          @reset="handleReset"
        />
      </div>

      <!-- Right Main Catalog (3-column grid) -->
      <main class="portal-catalog-content">
        <!-- Results Sub-header (only for BARBERSHOP sub-view toggle) -->
        <div v-if="isBarbershop && !isBarberOnly" class="catalog-results-header">
          <div class="barber-subview-toggle">
            <button
              type="button"
              class="subview-btn"
              :class="{ active: barbersSubView === 'barbers' }"
              @click="barbersSubView = 'barbers'"
            >
              <FontAwesomeIcon :icon="faScissors" />
              <span>{{ t("categories.barbers_tab") }}</span>
            </button>
            <button
              type="button"
              class="subview-btn"
              :class="{ active: barbersSubView === 'salons' }"
              @click="barbersSubView = 'salons'"
            >
              <FontAwesomeIcon :icon="faStore" />
              <span>{{ t("categories.salons_tab") }}</span>
            </button>
          </div>
        </div>

        <p v-if="message" class="catalog-message" role="status">
          {{ message }}
        </p>

        <!-- Loading State -->
        <div v-if="isLoading" class="catalog-empty">
          <span class="empty-icon"><FontAwesomeIcon :icon="isBarbershop ? faScissors : faStore" /></span>
          <p>{{ t("common.loading") }}</p>
        </div>

        <!-- Barbers View -->
        <template v-else-if="isBarbershop">
          <!-- 1. Barbers Sub-view -->
          <template v-if="isBarberOnly || barbersSubView === 'barbers'">
            <div v-if="!barbers.length" class="catalog-empty">
              <span class="empty-icon"><FontAwesomeIcon :icon="faScissors" /></span>
              <p>{{ t("filter.no_barbers_found") }}</p>
            </div>
            <div v-else class="bronla-cards-grid">
              <BarberCard
                v-for="barber in barbers"
                :key="barber.id"
                :barber="barber"
                @book="openBarberBooking"
                @info="openBarberInfo"
              />
            </div>
          </template>

          <!-- 2. Salons Sub-view -->
          <template v-else>
            <div v-if="!branches.length" class="catalog-empty">
              <span class="empty-icon"><FontAwesomeIcon :icon="faStore" /></span>
              <p>{{ t("filter.no_salons_found") }}</p>
            </div>
            <div v-else class="bronla-cards-grid">
              <BranchCard
                v-for="branch in branches"
                :key="branch.id"
                :branch="branch"
              />
            </div>
          </template>
        </template>

        <!-- Gaming Clubs View -->
        <template v-else>
          <div v-if="!branches.length" class="catalog-empty">
            <span class="empty-icon"><FontAwesomeIcon :icon="faStore" /></span>
            <p>{{ t("clubs.no_clubs_found") }}</p>
          </div>

          <div v-else class="bronla-cards-grid">
            <BranchCard
              v-for="branch in branches"
              :key="branch.id"
              :branch="branch"
            />
          </div>
        </template>
      </main>
    </div>

    <CatalogBottomSheet v-model="allServicesOpen" :title="t('catalog.all_services')" sheet-class="services-sheet">
      <div class="all-services-grid">
        <button
          v-for="service in serviceRows"
          :key="service.id"
          type="button"
          class="all-service-card"
          :class="{ selected: selectedServiceCode === service.code, 'service-root-card': service.depth === 0 }"
          :aria-pressed="selectedServiceCode === service.code"
          @click="setService(service.code)"
        >
          <span class="all-service-name">{{ service.label }}</span>
        </button>
        <p v-if="!serviceTypes.length" class="services-empty">Hozircha xizmat turlari yo‘q.</p>
      </div>
    </CatalogBottomSheet>

    <CatalogBottomSheet v-model="mobileFilterOpen" title="Filtr" sheet-class="filter-sheet">
      <div class="mobile-filter-body">
        <CatalogSidebarFilter
          v-model="draftFilterState"
          :show-sorting="false"
          :category="effectiveService?.code || ''"
          :service-options="serviceFilterOptions"
          :sub-view="barbersSubView"
          :locating="locating"
          @locate="locateDraft"
          @reset="resetDraftFilters"
        />
      </div>
      <template #footer>
        <div class="filter-sheet-actions">
          <button
            class="filter-clear-button"
            type="button"
            @click="clearMobileFilters"
          >
            Tozalash
          </button>
          <button class="filter-apply-button" type="button" @click="applyMobileFilters">
            {{ draftMatchesApplied ? `${totalCount} ta natijani ko‘rsatish` : "Natijalarni ko‘rsatish" }}
          </button>
        </div>
      </template>
    </CatalogBottomSheet>

    <!-- Barber Booking Modal -->
    <BarberBookingModal
      v-model="showBookingModal"
      :barber="selectedBarberForBooking"
      @booked="fetchBranches"
    />
  </div>
</template>

<style scoped>
.bronla-portal-container {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 0 40px;
}

.active-filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  min-width: 0;
}

.service-breadcrumbs { display: flex; gap: 6px; min-width: 0; }
.service-breadcrumbs { flex-wrap: wrap; align-items: center; width: fit-content; max-width: 100%; padding: 2px 8px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
.service-breadcrumbs button { min-height: 32px; padding: 3px 4px; border: 0; background: transparent; color: var(--accent); font-size: 12px; font-weight: 600; cursor: pointer; }
.service-breadcrumbs button + button::before { content: '›'; margin-right: 8px; color: var(--muted); }

.active-filter-chip {
  min-height: 34px;
  max-width: min(100%, 260px);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px 5px 12px;
  border: 1px solid color-mix(in srgb, var(--accent, #6366f1) 24%, var(--border));
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent, #6366f1) 8%, var(--surface));
  color: var(--accent, #6366f1);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.active-filter-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.portal-main-layout {
  display: grid;
  grid-template-columns: 290px 1fr;
  gap: 28px;
  align-items: start;
}

.portal-sidebar-wrapper {
  width: 100%;
}

.portal-catalog-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.catalog-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.results-count-badge {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.count-number {
  font-size: 22px;
  font-weight: 850;
  color: var(--text);
}

.count-label {
  font-size: 14px;
  font-weight: 650;
  color: var(--muted);
}

.barber-subview-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 4px;
  border-radius: 12px;
}

.subview-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.subview-btn:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}

.subview-btn.active {
  background: var(--accent, #6366f1);
  color: #ffffff;
}

.bronla-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
  gap: 14px;
}

.catalog-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 60px 20px;
  border-radius: 20px;
  border: 1px dashed var(--border);
  background: var(--surface);
  color: var(--muted);
  text-align: center;
}

.empty-icon {
  font-size: 38px;
  color: var(--muted);
  opacity: 0.6;
}

.mobile-filter-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: 10px;
}

.mobile-sort-select {
  min-width: 0;
  max-width: 58%;
  min-height: 44px;
  padding: 8px 30px 8px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 650;
}

.mobile-sort-control {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 36px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.mobile-sort-control::after { content: "⌄"; }
.mobile-sort-control:focus-within { outline: 2px solid var(--accent); }
.mobile-sort-control .mobile-sort-select { position: absolute; inset: 0; opacity: 0; width: 100%; height: 100%; max-width: none; cursor: pointer; }

.mobile-filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--control, rgba(255, 255, 255, 0.05));
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.mobile-results-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

@media (max-width: 1024px) {
  .portal-main-layout {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .mobile-filter-bar {
    display: flex;
  }

  .portal-sidebar-wrapper {
    display: none;
  }
}

@media (max-width: 640px) {
  :global(.customer-main:has(> .bronla-portal-container)) { padding-top: 8px; }
  .mobile-filter-bar { gap: 8px; }
  .mobile-filter-trigger { min-height: 36px; padding: 6px 10px; border-radius: 8px; font-size: 12px; }
  .mobile-sort-select { flex: 1; max-width: none; min-height: 36px; padding: 6px 10px; border-radius: 8px; font-size: 12px; }
  .bronla-portal-container {
    gap: 6px;
    padding: 0 0 24px;
  }

  .catalog-results-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .geo-locate-btn {
    width: 100%;
    justify-content: center;
  }

  .bronla-cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
}

@media (max-width: 400px) {
  .bronla-cards-grid {
    gap: 8px;
  }
}

.all-services-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 16px;
}

.all-service-card {
  position: relative;
  min-width: 0;
  min-height: 44px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 9px;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 3px 12px rgb(15 23 42 / 5%);
  text-align: left;
  cursor: pointer;
}

.all-service-card.selected { border-color: var(--accent, #6366f1); background: color-mix(in srgb, var(--accent, #6366f1) 8%, var(--surface)); }
.all-service-card.service-root-card { grid-column: 1 / -1; background: var(--control); }
.all-service-name { width: 100%; overflow-wrap: anywhere; font-size: 13px; line-height: 1.25; font-weight: 750; }
.services-empty { grid-column: 1 / -1; padding: 24px; color: var(--muted); text-align: center; }

.mobile-filter-body { padding: 10px 14px 12px; }
.mobile-filter-body :deep(.filter-sidebar) { position: static; top: auto; padding: 0; border: 0; border-radius: 0; background: transparent; box-shadow: none; backdrop-filter: none; -webkit-backdrop-filter: none; gap: 10px; }
.mobile-filter-body :deep(.filter-header) { display: none; }
.mobile-filter-body :deep(.filter-search-field) { min-height: 46px; }
.mobile-filter-body :deep(.select-box-item) { min-height: 44px; padding: 4px 6px; }
.mobile-filter-body :deep(.filter-group) { gap: 4px; }
.mobile-filter-body :deep(.select-box-list) { gap: 0; }
.filter-sheet-actions { display: flex; gap: 10px; padding: 12px 16px max(12px, env(safe-area-inset-bottom)); border-top: 1px solid var(--border); background: var(--surface); }
.filter-clear-button, .filter-apply-button { min-height: 48px; border-radius: 12px; font-size: 13px; font-weight: 750; cursor: pointer; }
.filter-clear-button { flex: 0 0 100px; border: 1px solid var(--border); background: var(--surface); color: var(--text); }
.filter-apply-button { flex: 1; padding: 0 12px; border: 1px solid var(--accent, #6366f1); background: var(--accent, #6366f1); color: white; }
.mobile-results-count { color: var(--muted); font-size: 12px; font-weight: 650; }

@media (max-width: 420px) {
  .filter-clear-button { flex-basis: 84px; }
  .all-services-grid { gap: 8px; padding: 12px; }
  .all-service-card { min-height: 44px; padding: 8px 10px; }
}
</style>
