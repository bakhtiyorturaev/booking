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

const cities = computed(() => [
  { id: "", name: t("filter.all_regions") || "Barcha hududlar" },
  { id: "Toshkent", name: t("filter.tashkent") || "Toshkent shahri" },
  { id: "Samarqand", name: t("filter.samarkand") || "Samarqand" },
  { id: "Buxoro", name: t("filter.bukhara") || "Buxoro" },
  { id: "Farg'ona", name: t("filter.fergana") || "Farg‘ona" },
  { id: "Namangan", name: t("filter.namangan") || "Namangan" },
  { id: "Andijon", name: t("filter.andijan") || "Andijon" },
])

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

const selectStatus = (statusValue: string) => {
  localState.status = localState.status === statusValue ? "" : statusValue
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
          :class="{ checked: !localState.status }"
          @click.prevent="selectStatus('')"
        >
          <span class="custom-checkbox">
            <svg
              v-if="!localState.status"
              class="check-icon"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z" />
            </svg>
          </span>
          <span class="select-box-label">{{ t("common.all") || "Barchasi" }}</span>
        </label>

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

    <!-- 4. Hududlar / Shaharlar -->
    <div class="filter-group">
      <h4 class="filter-group-heading">
        {{ t("filter.region_city") || "Hudud / Shahar" }}
      </h4>
      <div class="select-box-list">
        <label
          v-for="city in cities"
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

.filter-group-heading {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text);
  padding-bottom: 4px;
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

@media (max-width: 900px) {
  .filter-sidebar {
    position: static;
    border-radius: 12px;
    padding: 14px 12px;
  }
}
</style>
