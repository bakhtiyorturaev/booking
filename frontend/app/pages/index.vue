<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faGamepad,
  faScissors,
  faSliders,
  faStore,
} from "@fortawesome/free-solid-svg-icons"
import { useBranchesApi, type BranchListParams } from "~/api/branches"
import { useBarbersApi } from "~/api/barbers"
import BranchCard from "~/components/catalog/BranchCard.vue"
import BarberCard from "~/components/catalog/BarberCard.vue"
import BarberBookingModal from "~/components/catalog/BarberBookingModal.vue"
import CatalogSidebarFilter, { type FilterState } from "~/components/catalog/CatalogSidebarFilter.vue"
import type { BarberItem } from "~/types/barber"

definePageMeta({ layout: "customer" })

const branchesApi = useBranchesApi()
const barbersApi = useBarbersApi()
const { locale, load, t } = useTranslations()
await load()

const activeCategory = ref<"GAMING_CLUB" | "BARBERSHOP">("GAMING_CLUB")

useHead({
  title: computed(() =>
    activeCategory.value === "BARBERSHOP"
      ? (t("barbers.all_barbershops") || "Sartaroshxonalar va Sartaroshlar")
      : (t("clubs.catalog_title") || "Barcha klublar")
  ),
})

const filterState = ref<FilterState>({
  search: "",
  city: "",
  ordering: "",
  service_type: "",
  status: "",
})

const userCoords = ref<{ latitude: number; longitude: number } | null>(null)
const locating = ref(false)
const isLoading = ref(false)
const mobileFilterOpen = ref(false)
const { message, show: showMessage, clear: clearMessage } = useTimedMessage()

const barbers = ref<BarberItem[]>([])
const selectedBarberForBooking = ref<BarberItem | null>(null)
const showBookingModal = ref(false)
const barbersSubView = ref<"barbers" | "salons">("barbers")

function extractList<T>(res: any): T[] {
  if (!res) return []
  if (Array.isArray(res)) return res
  if (Array.isArray(res.results)) return res.results
  if (Array.isArray(res.data)) return res.data
  return []
}

const fetchBranches = async () => {
  isLoading.value = true
  clearMessage()
  try {
    const params: BranchListParams = {
      category: activeCategory.value,
      search: filterState.value.search || undefined,
      city: filterState.value.city || undefined,
      service_type: filterState.value.service_type || undefined,
      ordering: filterState.value.ordering || undefined,
    }
    if (filterState.value.ordering === "distance" && userCoords.value) {
      params.latitude = userCoords.value.latitude
      params.longitude = userCoords.value.longitude
    }
    const response = await branchesApi.list(params)
    data.value = response

    if (activeCategory.value === "BARBERSHOP") {
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
    }
  } catch (err: any) {
    console.error("Fetch catalog error:", err)
  } finally {
    isLoading.value = false
  }
}

const { data, data: initialBranches } = await useAsyncData("branch-catalog", () => {
  return branchesApi.list({ category: "GAMING_CLUB", ordering: "-rating" })
})

const { data: initialBarbers } = await useAsyncData("barbers-catalog", () => {
  return barbersApi.getBarbers({ ordering: "-rating" })
})

if (initialBarbers.value) {
  barbers.value = extractList<BarberItem>(initialBarbers.value)
}

const branches = computed(() => data.value?.results ?? [])
const totalCount = computed(() => {
  if (activeCategory.value === "BARBERSHOP") {
    return barbersSubView.value === "barbers" ? barbers.value.length : branches.value.length
  }
  return data.value?.count ?? branches.value.length
})

const setCategory = (cat: "GAMING_CLUB" | "BARBERSHOP") => {
  if (activeCategory.value === cat) return
  activeCategory.value = cat
  filterState.value.service_type = ""
  filterState.value.status = ""
  filterState.value.ordering = "-rating"
  void fetchBranches()
}

watch(
  filterState,
  () => {
    void fetchBranches()
  },
  { deep: true },
)

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

const handleReset = () => {
  userCoords.value = null
  void fetchBranches()
}

const openBarberBooking = (barber: BarberItem) => {
  selectedBarberForBooking.value = barber
  showBookingModal.value = true
}
</script>

<template>
  <div class="bronla-portal-container">
    <!-- Category Tabs Navigation -->
    <div class="category-tabs-bar">
      <button
        type="button"
        class="category-tab-btn"
        :class="{ active: activeCategory === 'GAMING_CLUB' }"
        @click="setCategory('GAMING_CLUB')"
      >
        <span>{{ t("categories.gaming_clubs") }}</span>
      </button>

      <button
        type="button"
        class="category-tab-btn"
        :class="{ active: activeCategory === 'BARBERSHOP' }"
        @click="setCategory('BARBERSHOP')"
      >
        <span>{{ t("categories.barbershops") }}</span>
      </button>
    </div>

    <!-- Main 2-Column Content Layout -->
    <div class="portal-main-layout">
      <!-- Mobile Filter Toggle Button -->
      <div class="mobile-filter-bar">
        <button
          type="button"
          class="mobile-filter-trigger"
          @click="mobileFilterOpen = !mobileFilterOpen"
        >
          <FontAwesomeIcon :icon="faSliders" />
          <span>{{ t("filter.title") }}</span>
        </button>
      </div>

      <!-- Left Sidebar Filter -->
      <div class="portal-sidebar-wrapper" :class="{ 'mobile-open': mobileFilterOpen }">
        <CatalogSidebarFilter
          v-model="filterState"
          :category="activeCategory"
          :sub-view="barbersSubView"
          :locating="locating"
          @locate="locate"
          @reset="handleReset"
        />
      </div>

      <!-- Right Main Catalog (3-column grid) -->
      <main class="portal-catalog-content">
        <!-- Results Sub-header (only for BARBERSHOP sub-view toggle) -->
        <div v-if="activeCategory === 'BARBERSHOP'" class="catalog-results-header">
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
          <span class="empty-icon"><FontAwesomeIcon :icon="activeCategory === 'BARBERSHOP' ? faScissors : faGamepad" /></span>
          <p>{{ t("common.loading") }}</p>
        </div>

        <!-- Barbers View -->
        <template v-else-if="activeCategory === 'BARBERSHOP'">
          <!-- 1. Barbers Sub-view -->
          <template v-if="barbersSubView === 'barbers'">
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

.category-tabs-bar {
  display: flex;
  gap: 6px;
  padding: 4px;
  background: var(--surface, #1e293b);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  width: fit-content;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.category-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  border-radius: 9px;
  border: none;
  background: transparent;
  color: var(--muted, #94a3b8);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.category-tab-btn:hover {
  color: var(--text, #f8fafc);
  background: rgba(255, 255, 255, 0.05);
}

.category-tab-btn.active {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
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
  padding: 10px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
}

.mobile-filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
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
    gap: 18px;
  }

  .mobile-filter-bar {
    display: flex;
  }

  .portal-sidebar-wrapper {
    display: none;
  }

  .portal-sidebar-wrapper.mobile-open {
    display: block;
    animation: fadeIn 0.2s ease;
  }
}

@media (max-width: 640px) {
  .bronla-portal-container {
    gap: 16px;
    padding: 6px 0 30px;
  }

  .category-tabs-bar {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    padding: 4px;
  }

  .category-tab-btn {
    justify-content: center;
    padding: 9px 8px;
    font-size: 13px;
    gap: 6px;
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
</style>
