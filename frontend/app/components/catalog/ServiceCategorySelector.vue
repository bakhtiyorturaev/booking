<script setup lang="ts">
import type { ServiceTypeOption } from "~/api/serviceTypes"

const props = defineProps<{
  services: ServiceTypeOption[]
  selectedCode: string | null
  loading?: boolean
}>()
const emit = defineEmits<{
  (event: "select", code: string): void
  (event: "all"): void
}>()
const strip = ref<HTMLElement | null>(null)
const visibleCount = ref(2)
const itemWidth = ref(92)
const { t } = useTranslations()
let observer: ResizeObserver | null = null

const visibleServices = computed(() => {
  const visible = props.services.slice(0, visibleCount.value)
  const selected = props.services.find(service => service.code === props.selectedCode)
  if (selected && visible.length && !visible.some(service => service.id === selected.id)) {
    visible[visible.length - 1] = selected
  }
  return visible
})

onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    if (!entry) return
    const width = entry.contentRect.width
    itemWidth.value = width >= 600 ? 120 : 92
    visibleCount.value = Math.max(0, Math.floor((width - 72) / (itemWidth.value + 6)))
  })
  if (strip.value) observer.observe(strip.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <nav class="service-selector" aria-label="Xizmat turlari">
    <div ref="strip" class="service-strip">
      <button
        v-for="service in visibleServices"
        :key="service.id"
        type="button"
        class="service-card"
        :style="{ width: `${itemWidth}px` }"
        :class="{ selected: selectedCode === service.code }"
        :aria-pressed="selectedCode === service.code"
        :title="service.name"
        @click="emit('select', service.code)"
      >
        <span>{{ service.name }}</span>
      </button>
      <button class="service-card service-all" type="button" aria-haspopup="dialog" @click="emit('all')">
        {{ t("catalog.all") }}
      </button>
      <span v-if="loading && !services.length" class="service-loading" aria-live="polite">Yuklanmoqda…</span>
    </div>
  </nav>
</template>

<style scoped>
.service-selector { min-width: 0; width: 100%; }
.service-strip { display: flex; flex-wrap: nowrap; align-items: center; gap: 6px; width: 100%; overflow: hidden; padding-block: 4px; }
.service-card { position: relative; flex: 0 0 auto; min-width: 0; max-width: 100%; min-height: 36px; padding: 6px 9px; border: 1px solid var(--border, #e2e8f0); border-radius: 8px; background: var(--surface, #fff); color: var(--muted, #64748b); font-size: 12px; font-weight: 700; cursor: pointer; transition: border-color .16s ease, background .16s ease, color .16s ease; }
.service-card span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.service-card.selected { border-color: var(--accent, #6366f1); background: color-mix(in srgb, var(--accent, #6366f1) 10%, var(--surface, #fff)); color: var(--accent, #6366f1); }
.service-card:focus-visible { outline: 2px solid var(--accent, #6366f1); outline-offset: -2px; }
.service-all { width: 72px; color: var(--accent, #6366f1); }
.service-loading { color: var(--muted, #64748b); font-size: 12px; }
@media (max-width: 1024px) { .service-card { min-height: 32px; padding: 5px 7px; } .service-card::after { content: ""; position: absolute; inset: -6px 0; } }
</style>
