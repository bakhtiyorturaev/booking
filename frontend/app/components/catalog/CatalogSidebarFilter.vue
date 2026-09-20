<script setup lang="ts">
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

const isRegionSectionOpen = ref(true)
const showAllRegions = ref(false)

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
    return props.subView === "barbers"
      ? (t("filter.search_barbers_placeholder") || "Sartarosh ismi...")
      : (t("filter.search_salons_placeholder") || "Sartaroshxona nomi...")
  }
  return t("filter.search_placeholder") || "Qidirish..."
})

const allCities = computed(() => [
  { id: "Toshkent", name: "Toshkent shahri" },
  { id: "Toshkent viloyati", name: "Toshkent viloyati" },
  { id: "Samarqand", name: "Samarqand" },
  { id: "Buxoro", name: "Buxoro" },
  { id: "Farg'ona", name: "Farg‘ona" },
  { id: "Andijon", name: "Andijon" },
  { id: "Namangan", name: "Namangan" },
  { id: "Qashqadaryo", name: "Qashqadaryo" },
  { id: "Surxondaryo", name: "Surxondaryo" },
  { id: "Xorazm", name: "Xorazm" },
  { id: "Navoiy", name: "Navoiy" },
  { id: "Jizzax", name: "Jizzax" },
  { id: "Sirdaryo", name: "Sirdaryo" },
  { id: "Qoraqalpog'iston", name: "Qoraqalpog‘iston" },
])

const displayedCities = computed(() => {
  if (showAllRegions.value) return allCities.value
  const top = allCities.value.slice(0, 5)
  if (localState.city && !top.some(c => c.id === localState.city)) {
    const selected = allCities.value.find(c => c.id === localState.city)
    if (selected) top.push(selected)
  }
  return top
})

const selectedCityLabel = computed(() => {
  if (!localState.city) return ""
  const found = allCities.value.find(c => c.id === localState.city)
  return found ? found.name : localState.city
})

const sortOptions = computed(() => {
  if (props.category === "BARBERSHOP") {
    return [
      { value: "-rating", label: t("filter.sort_rating") || "Reyting bo‘yicha" },
      { value: "distance", label: t("filter.sort_nearest") || "Eng yaqin masofada" },
    ]
  }
  return [
    { value: "-rating", label: t("filter.sort_rating") || "Reyting bo‘yicha" },
    { value: "distance", label: t("filter.sort_nearest") || "Eng yaqin masofada" },
    { value: "price", label: t("filter.sort_price_asc") || "Narx: Arzondan qimmatga" },
    { value: "-price", label: t("filter.sort_price_desc") || "Narx: Qimmatdan arzonga" },
  ]
})

const selectSort = (val: string) => {
  if (localState.ordering === val) {
    localState.ordering = ""
  } else {
    if (val === "distance") {
      emit("locate")
    }
    localState.ordering = val
  }
  emitUpdate()
}

const selectCity = (cityId: string) => {
  localState.city = localState.city === cityId ? "" : cityId
  emitUpdate()
}

const selectService = (type: string) => {
  localState.service_type = localState.service_type === type ? "" : type
  emitUpdate()
}

const selectStatus = (statusValue: string) => {
  localState.status = localState.status === statusValue ? "" : statusValue
  emitUpdate()
}

const resetFilters = () => {
  localState.search = ""
  localState.city = ""
  localState.ordering = ""
  localState.service_type = ""
  localState.status = ""
  localState.min_rating = undefined
  localState.min_price_tiyin = undefined
  localState.max_price_tiyin = undefined
  emit("reset")
  emitUpdate()
}
</script>

<template>
  <aside class="filter-sidebar">
    <!-- Header -->
    <div class="filter-header">
      <h3 class="filter-title">
        {{ t("filter.title") || "Filtrlar" }}
      </h3>
      <button
        type="button"
        class="filter-reset-link"
        @click="resetFilters"
      >
        {{ t("filter.reset") || "Tozalash" }}
      </button>
    </div>

    <!-- 1. Search Box -->
    <div class="filter-group">
      <input
        v-model="localState.search"
        type="text"
        :placeholder="searchPlaceholder"
        class="filter-search-field"
        @input="onSearchInput"
      >
    </div>

    <!-- 2. Services / Features (Faqat O'yin klublari uchun) -->
    <div v-if="props.category === 'GAMING_CLUB'" class="filter-group">
      <h4 class="filter-group-heading">
        {{ t("filter.service_type") || "Xizmat turi" }}
      </h4>
      <div class="select-box-list">
        <label
          class="select-box-item"
          :class="{ checked: localState.service_type === 'PLAYSTATION' || localState.service_type === 'PS' }"
          @click.prevent="selectService('PLAYSTATION')"
        >
          <span class="custom-checkbox">
            <svg
              v-if="localState.service_type === 'PLAYSTATION' || localState.service_type === 'PS'"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">PlayStation</span>
        </label>

        <label
          class="select-box-item"
          :class="{ checked: localState.service_type === 'COMPUTER' || localState.service_type === 'PC' }"
          @click.prevent="selectService('COMPUTER')"
        >
          <span class="custom-checkbox">
            <svg
              v-if="localState.service_type === 'COMPUTER' || localState.service_type === 'PC'"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">Cyber / PC</span>
        </label>
      </div>
    </div>

    <!-- 3. Sartarosh holati (Faqat Barbershop ustalar uchun) -->
    <div v-if="props.category === 'BARBERSHOP' && props.subView === 'barbers'" class="filter-group">
      <h4 class="filter-group-heading">
        {{ t("barbers.status") || "Usta holati" }}
      </h4>
      <div class="select-box-list">
        <label
          class="select-box-item"
          :class="{ checked: localState.status === 'AVAILABLE' }"
          @click.prevent="selectStatus('AVAILABLE')"
        >
          <span class="custom-checkbox">
            <svg
              v-if="localState.status === 'AVAILABLE'"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">{{ t("barbers.status_available") || "Ishda" }}</span>
        </label>

        <label
          class="select-box-item"
          :class="{ checked: localState.status === 'BREAK' }"
          @click.prevent="selectStatus('BREAK')"
        >
          <span class="custom-checkbox">
            <svg
              v-if="localState.status === 'BREAK'"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">{{ t("barbers.status_break") || "Tanaffusda" }}</span>
        </label>
      </div>
    </div>

    <!-- 4. Hududlar / Shaharlar (Ochilib-yopiladigan accordion + Yana ko'rsatish) -->
    <div class="filter-group">
      <div
        class="filter-group-header"
        @click="isRegionSectionOpen = !isRegionSectionOpen"
      >
        <h4 class="filter-group-heading">
          {{ t("filter.region_city") || "Hudud / Shahar" }}
          <span v-if="selectedCityLabel && !isRegionSectionOpen" class="selected-badge">
            ({{ selectedCityLabel }})
          </span>
        </h4>
        <span class="accordion-arrow" :class="{ open: isRegionSectionOpen }">
          <svg viewBox="0 0 16 16" width="12" height="12" fill="currentColor">
            <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z" />
          </svg>
        </span>
      </div>

      <div v-show="isRegionSectionOpen" class="select-box-list">
        <label
          v-for="city in displayedCities"
          :key="city.id"
          class="select-box-item"
          :class="{ checked: localState.city === city.id }"
          @click.prevent="selectCity(city.id)"
        >
          <span class="custom-checkbox">
            <svg
              v-if="localState.city === city.id"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">{{ city.name }}</span>
        </label>

        <button
          type="button"
          class="toggle-more-btn"
          @click="showAllRegions = !showAllRegions"
        >
          {{ showAllRegions ? "Kamroq ko‘rsatish ↑" : `Barcha ${allCities.length} ta viloyatni ko‘rsatish ↓` }}
        </button>
      </div>
    </div>

    <!-- 5. Saralash -->
    <div class="filter-group">
      <h4 class="filter-group-heading">
        {{ t("filter.sort_by") || "Saralash" }}
      </h4>
      <div class="select-box-list">
        <label
          v-for="opt in sortOptions"
          :key="opt.value"
          class="select-box-item"
          :class="{ checked: localState.ordering === opt.value }"
          @click.prevent="selectSort(opt.value)"
        >
          <span class="custom-checkbox">
            <svg
              v-if="localState.ordering === opt.value"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">{{ opt.label }}</span>
        </label>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.filter-sidebar {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 85px;
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.filter-title {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.01em;
}

.filter-reset-link {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  transition: color 0.15s ease;
}

.filter-reset-link:hover {
  color: var(--accent);
  text-decoration: underline;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  padding-bottom: 2px;
}

.filter-group-heading {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text);
  display: flex;
  align-items: center;
}

.selected-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  margin-left: 6px;
}

.accordion-arrow {
  color: var(--muted);
  transition: transform 0.2s ease;
  display: flex;
  align-items: center;
}

.accordion-arrow.open {
  transform: rotate(180deg);
}

.filter-search-field {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 13px;
  outline: 0;
  transition: border-color 0.15s ease;
}

.filter-search-field:focus {
  border-color: var(--accent);
}

.select-box-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.select-box-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 6px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.12s ease;
}

.select-box-item:hover {
  background: color-mix(in srgb, var(--control) 50%, transparent);
}

.custom-checkbox {
  width: 17px;
  height: 17px;
  border-radius: 4px;
  border: 1.5px solid var(--border);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.select-box-item.checked .custom-checkbox {
  background: #0284c7;
  border-color: #0284c7;
}

.check-icon {
  width: 12px;
  height: 12px;
  color: #ffffff;
}

.select-box-label {
  font-size: 13.5px;
  color: var(--text);
  font-weight: 450;
  line-height: 1.35;
  transition: color 0.12s ease;
}

.select-box-item.checked .select-box-label {
  font-weight: 600;
  color: var(--text);
}

.toggle-more-btn {
  background: transparent;
  border: 0;
  color: var(--accent);
  font-size: 12px;
  font-weight: 650;
  text-align: left;
  padding: 6px 6px 2px;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.toggle-more-btn:hover {
  text-decoration: underline;
  opacity: 0.9;
}

@media (max-width: 900px) {
  .filter-sidebar {
    position: static;
    border-radius: 12px;
    padding: 14px 12px;
  }
}
</style>
