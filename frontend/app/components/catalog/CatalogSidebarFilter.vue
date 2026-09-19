<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faChevronDown,
  faFilter,
  faLocationCrosshairs,
  faMagnifyingGlass,
  faRotateLeft,
  faStar,
} from "@fortawesome/free-solid-svg-icons"
import { useTranslations } from "~/composables/useTranslations"

export interface FilterState {
  search: string
  city: string
  ordering: string
  service_type: string
  status?: string
  min_rating?: number
  min_price_tiyin?: number
  max_price_tiyin?: number
}

const props = withDefaults(
  defineProps<{
    modelValue: FilterState
    category?: "GAMING_CLUB" | "BARBERSHOP"
    subView?: "barbers" | "salons"
    locating?: boolean
  }>(),
  {
    category: "GAMING_CLUB",
    subView: "barbers",
    locating: false,
  },
)

const emit = defineEmits<{
  (e: "update:modelValue", value: FilterState): void
  (e: "locate" | "reset"): void
}>()

const { t } = useTranslations()

const localState = reactive<FilterState>({
  ...props.modelValue,
})

const isCityAccordionOpen = ref(false)

watch(
  () => props.modelValue,
  (val) => {
    Object.assign(localState, val)
  },
  { deep: true },
)

const emitUpdate = () => {
  emit("update:modelValue", { ...localState })
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null
const onSearchInput = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emitUpdate()
  }, 300)
}

const searchPlaceholder = computed(() => {
  if (props.category === "BARBERSHOP") {
    return props.subView === "barbers" ? t("filter.search_barbers_placeholder") : t("filter.search_salons_placeholder")
  }
  return t("filter.search_placeholder") || "Klub nomi bo'yicha..."
})

const cities = computed(() => [
  { id: "", name: t("filter.all_regions") },
  { id: "Toshkent", name: t("filter.tashkent") },
  { id: "Samarqand", name: t("filter.samarkand") },
  { id: "Buxoro", name: t("filter.bukhara") },
  { id: "Farg'ona", name: t("filter.fergana") },
  { id: "Namangan", name: t("filter.namangan") },
  { id: "Andijon", name: t("filter.andijan") },
])

const selectedCityName = computed(() => {
  if (!localState.city) return ""
  const found = cities.value.find(c => c.id === localState.city)
  return found ? found.name : localState.city
})

const sortOptions = computed(() => {
  if (props.category === "BARBERSHOP" && props.subView === "barbers") {
    return [
      { value: "-rating", label: t("filter.sort_highest_rating"), icon: faStar },
      { value: "distance", label: t("filter.sort_nearest"), icon: faLocationCrosshairs },
    ]
  }
  if (props.category === "BARBERSHOP" && props.subView === "salons") {
    return [
      { value: "-rating", label: t("filter.sort_highest_rating"), icon: faStar },
      { value: "distance", label: t("filter.sort_nearest"), icon: faLocationCrosshairs },
    ]
  }
  return [
    { value: "-rating", label: t("filter.sort_rating"), icon: faStar },
    { value: "distance", label: t("filter.sort_nearest"), icon: faLocationCrosshairs },
    { value: "price", label: t("filter.sort_price_asc"), icon: null },
    { value: "-price", label: t("filter.sort_price_desc"), icon: null },
  ]
})

const selectSort = (val: string) => {
  if (val === "distance") {
    emit("locate")
  }
  localState.ordering = val
  emitUpdate()
}

const selectCity = (cityId: string) => {
  localState.city = cityId
  emitUpdate()
}

const selectService = (type: string) => {
  localState.service_type = localState.service_type === type ? "" : type
  emitUpdate()
}

const resetFilters = () => {
  localState.search = ""
  localState.city = ""
  localState.ordering = "-rating"
  localState.service_type = ""
  localState.status = ""
  localState.min_rating = undefined
  localState.min_price_tiyin = undefined
  localState.max_price_tiyin = undefined
  isCityAccordionOpen.value = false
  emit("reset")
  emitUpdate()
}
</script>

<template>
  <aside class="bronla-sidebar-filter">
    <!-- Header -->
    <div class="filter-card-header">
      <div class="filter-header-left">
        <FontAwesomeIcon :icon="faFilter" class="filter-icon" />
        <h2>{{ t("filter.title") || "Filtrlar" }}</h2>
      </div>
      <button
        type="button"
        class="filter-reset-btn"
        :title="t('filter.reset')"
        @click="resetFilters"
      >
        <FontAwesomeIcon :icon="faRotateLeft" />
        <span>{{ t("filter.reset") }}</span>
      </button>
    </div>

    <!-- 1. Search Box -->
    <div class="filter-section">
      <div class="filter-search-box">
        <FontAwesomeIcon :icon="faMagnifyingGlass" class="search-svg" />
        <input
          v-model="localState.search"
          type="text"
          :placeholder="searchPlaceholder"
          class="filter-search-input"
          @input="onSearchInput"
        >
      </div>
    </div>

    <!-- 2. Sort Options -->
    <div class="filter-section">
      <label class="filter-section-label">{{ t("filter.sort_by") || "Saralash" }}</label>
      <div class="sort-pills-list" :class="{ 'single-row': sortOptions.length <= 2, 'single-item': sortOptions.length === 1 }">
        <button
          v-for="opt in sortOptions"
          :key="opt.value"
          type="button"
          class="sort-pill"
          :class="{ active: localState.ordering === opt.value }"
          @click="selectSort(opt.value)"
        >
          <FontAwesomeIcon v-if="opt.icon" :icon="opt.icon" :spin="opt.value === 'distance' && locating" />
          <span>{{ opt.label }}</span>
        </button>
      </div>
    </div>

    <!-- 3. Cities / Regions (Collapsible Accordion) -->
    <div class="filter-section filter-accordion-section">
      <button
        type="button"
        class="filter-accordion-header"
        @click="isCityAccordionOpen = !isCityAccordionOpen"
      >
        <div class="accordion-title-block">
          <span class="filter-section-label">{{ t("filter.region_city") }}</span>
          <span v-if="selectedCityName" class="selected-city-tag">
            {{ selectedCityName }}
          </span>
        </div>
        <FontAwesomeIcon
          :icon="faChevronDown"
          class="accordion-chevron"
          :class="{ open: isCityAccordionOpen }"
        />
      </button>

      <div v-show="isCityAccordionOpen" class="city-chips-grid">
        <button
          v-for="c in cities"
          :key="c.id"
          type="button"
          class="city-chip"
          :class="{ active: localState.city === c.id }"
          @click="selectCity(c.id)"
        >
          {{ c.name }}
        </button>
      </div>
    </div>

    <!-- 4. Service Type (Faqat Gaming Clublar uchun) -->
    <div v-if="props.category === 'GAMING_CLUB'" class="filter-section">
      <div class="service-toggle-group">
        <button
          type="button"
          class="service-toggle-btn"
          :class="{ active: localState.service_type === 'PLAYSTATION' || localState.service_type === 'PS' }"
          @click="selectService('PLAYSTATION')"
        >
          🎮 PlayStation
        </button>
        <button
          type="button"
          class="service-toggle-btn"
          :class="{ active: localState.service_type === 'COMPUTER' || localState.service_type === 'PC' }"
          @click="selectService('COMPUTER')"
        >
          💻 Cyber / PC
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.bronla-sidebar-filter {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 90px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.filter-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.filter-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-icon {
  color: var(--accent);
  font-size: 15px;
}

.filter-card-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.01em;
}

.filter-reset-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  padding: 3px 6px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.filter-reset-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.filter-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-section-label {
  font-size: 12.5px;
  font-weight: 750;
  color: var(--text);
}

.filter-search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-svg {
  position: absolute;
  left: 12px;
  color: var(--muted);
  font-size: 13px;
  pointer-events: none;
}

.filter-search-input {
  width: 100%;
  height: 38px;
  padding: 0 12px 0 34px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--control, rgba(255, 255, 255, 0.04));
  color: var(--text);
  font-size: 12.5px;
  outline: 0;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.filter-search-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 25%, transparent);
}

.sort-pills-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.sort-pills-list.single-row {
  grid-template-columns: 1fr 1fr;
}

.sort-pills-list.single-item {
  grid-template-columns: 1fr;
}

.sort-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 34px;
  padding: 0 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  text-align: center;
  transition: all 0.15s ease;
}

.sort-pill:hover {
  color: var(--text);
  border-color: var(--accent);
  background: color-mix(in srgb, var(--control) 50%, transparent);
}

.sort-pill.active {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-text);
  font-weight: 750;
}

/* Collapsible Accordion */
.filter-accordion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: color-mix(in srgb, var(--control) 60%, transparent);
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-accordion-header:hover {
  border-color: var(--accent);
}

.accordion-title-block {
  display: flex;
  align-items: center;
  gap: 6px;
}

.selected-city-tag {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1.5px 6px;
  border-radius: 5px;
  background: var(--accent);
  color: var(--accent-text);
}

.accordion-chevron {
  font-size: 11px;
  color: var(--muted);
  transition: transform 0.2s ease;
}

.accordion-chevron.open {
  transform: rotate(180deg);
  color: var(--accent);
}

.city-chips-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding-top: 4px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.city-chip {
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.15s ease;
}

.city-chip:hover {
  border-color: var(--accent);
  color: var(--text);
}

.city-chip.active {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 750;
}

.service-toggle-group {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.service-toggle-btn {
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.service-toggle-btn:hover {
  border-color: var(--accent);
  color: var(--text);
}

.service-toggle-btn.active {
  background: #10b981;
  border-color: #10b981;
  color: #ffffff;
}
</style>
