<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faMagnifyingGlass, faXmark, faCheck } from "@fortawesome/free-solid-svg-icons"
import type { SearchSelectOption, SearchSelectPage } from "~/types/searchSelect"

const props = defineProps<{
  modelValue: SearchSelectOption | null
  fetchOptions: (query: string, page: number) => Promise<SearchSelectPage>
  label: string
  placeholder?: string
  disabled?: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: SearchSelectOption | null] }>()
const id = useId()
const root = ref<HTMLElement | null>(null)
const input = ref<HTMLInputElement | null>(null)
const opened = ref(false)
const query = ref("")
const options = ref<SearchSelectOption[]>([])
const loading = ref(false)
const error = ref("")
const page = ref(1)
const hasNext = ref(false)
const active = ref(-1)
let version = 0
let timer: ReturnType<typeof setTimeout> | undefined
const load = async (append = false) => {
  const current = ++version
  loading.value = true
  error.value = ""
  const nextPage = append ? page.value + 1 : 1
  try {
    const result = await props.fetchOptions(query.value.trim(), nextPage)
    if (current !== version) return
    const combined = append ? [...options.value, ...result.options] : result.options
    options.value = [...new Map(combined.map(option => [option.value, option])).values()]
    page.value = nextPage
    hasNext.value = result.hasNext
    active.value = append ? active.value : -1
  } catch {
    if (current === version) error.value = "Qidiruvni yuklab bo‘lmadi. Qayta urining."
  } finally {
    if (current === version) loading.value = false
  }
}
const close = () => { opened.value = false; version++; clearTimeout(timer); loading.value = false }
const begin = () => {
  if (props.disabled || opened.value) return
  opened.value = true
  query.value = ""
  options.value = []
  active.value = -1
  void load()
}
const search = (event: Event) => {
  if (props.modelValue) emit('update:modelValue', null)
  error.value = ""
  query.value = (event.target as HTMLInputElement).value
  opened.value = true
  version++
  options.value = []
  active.value = -1
  loading.value = true
  clearTimeout(timer)
  timer = setTimeout(() => { void load() }, 250)
}
const select = (option: SearchSelectOption) => {
  emit('update:modelValue', option)
  close()
  input.value?.focus()
}
const clear = () => { emit('update:modelValue', null); close(); input.value?.focus() }
const keydown = (event: KeyboardEvent) => {
  if (event.key === "Escape" && opened.value) { event.preventDefault(); event.stopPropagation(); close(); return }
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault()
    if (!opened.value) { begin(); return }
    if (!options.value.length) return
    active.value = (active.value + (event.key === "ArrowDown" ? 1 : -1) + options.value.length) % options.value.length
    void nextTick(() => root.value?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" }))
  } else if (event.key === "Enter" && opened.value) {
    event.preventDefault()
    const option = options.value[active.value]
    if (option) select(option)
  }
}
const outside = (event: PointerEvent) => { if (!root.value?.contains(event.target as Node)) close() }
const focusout = (event: FocusEvent) => { if (!root.value?.contains(event.relatedTarget as Node)) close() }
onMounted(() => document.addEventListener("pointerdown", outside))
onBeforeUnmount(() => { close(); document.removeEventListener("pointerdown", outside) })
</script>

<template>
  <div ref="root" class="remote-select" @focusout="focusout">
    <div class="search-control" :class="{ expanded: opened, disabled }">
      <FontAwesomeIcon :icon="faMagnifyingGlass" aria-hidden="true" />
      <input :id="id" ref="input" type="text" role="combobox" :aria-label="label" :aria-expanded="opened" :aria-controls="`${id}-results`" :aria-activedescendant="active >= 0 && opened ? `${id}-option-${active}` : undefined" aria-autocomplete="list" :value="opened ? query : modelValue?.label || ''" :placeholder="placeholder || 'Qidirish…'" :disabled="disabled" autocomplete="off" @focus="begin" @input="search" @keydown="keydown">
      <button v-if="modelValue" type="button" class="clear-option" :aria-label="`${label} tanlovini tozalash`" :disabled="disabled" @click="clear"><FontAwesomeIcon :icon="faXmark" /></button>
    </div>
    <small v-if="modelValue?.description && !opened" class="selected-description">{{ modelValue.description }}</small>
    <div v-if="opened" class="search-dropdown">
      <div :id="`${id}-results`" role="listbox" :aria-label="label" :aria-busy="loading" class="search-options">
        <button v-for="(option, index) in options" :id="`${id}-option-${index}`" :key="option.value" type="button" role="option" tabindex="-1" :aria-selected="index === active" class="search-option" :class="{ highlighted: index === active }" @pointerdown.prevent @click="select(option)">
          <span><strong>{{ option.label }}</strong><small v-if="option.description">{{ option.description }}</small></span><FontAwesomeIcon v-if="option.value === modelValue?.value" :icon="faCheck" />
        </button>
      </div>
      <p v-if="error" class="search-status" role="alert">{{ error }} <button type="button" @click="load()">Qayta urinish</button></p>
      <p v-else-if="loading" class="search-status" role="status">Qidirilmoqda…</p>
      <p v-else-if="!options.length" class="search-status" role="status">Natija topilmadi.</p>
      <button v-else-if="hasNext" type="button" class="load-more" @click="load(true)">Yana ko‘rsatish</button>
    </div>
  </div>
</template>

<style scoped>
.remote-select { position: relative; min-width: 0; }
.search-control { display: flex; align-items: center; min-height: 44px; border: 1px solid var(--border); border-radius: 10px; background: var(--control); transition: border-color .15s; }
.search-control.expanded, .search-control:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent); }
.search-control > svg { margin-left: 12px; flex-shrink: 0; color: var(--muted); font-size: 12px; }
.search-control input { width: 100%; min-width: 0; height: 42px; padding: 10px; border: 0; outline: 0; background: transparent; color: var(--text); font: inherit; font-size: 13px; box-shadow: none; }
.remote-select .search-control input:focus-visible { outline: none; box-shadow: none; }
.search-control.disabled { opacity: .55; }
.clear-option { display: grid; place-items: center; width: 34px; height: 38px; margin-right: 3px; padding: 0; border: 0; background: transparent; color: var(--muted); cursor: pointer; }
.selected-description { display: block; margin-top: 5px; color: var(--muted); font-size: 11px; }
.search-dropdown { position: absolute; z-index: 30; inset: calc(100% + 5px) 0 auto; overflow: hidden; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); box-shadow: 0 12px 30px #0f172a20; }
.search-options { max-height: 220px; overflow-y: auto; }
.search-option { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; padding: 11px 13px; border: 0; background: transparent; color: var(--text); font: inherit; text-align: left; cursor: pointer; }
.search-option > span { display: grid; gap: 4px; min-width: 0; }.search-option strong { font-size: 13px; font-weight: 600; overflow-wrap: anywhere; }.search-option small { font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.search-option:hover, .search-option.highlighted { background: color-mix(in srgb, var(--accent) 9%, transparent); }
.search-option > svg { color: var(--accent); font-size: 12px; flex-shrink: 0; }
.search-status { margin: 0; padding: 14px; color: var(--muted); font-size: 12px; }.search-status button, .load-more { border: 0; background: transparent; color: var(--accent); font: inherit; cursor: pointer; }.load-more { min-height: 40px; width: 100%; border-top: 1px solid var(--border); font-size: 12px; }
@media (max-width: 600px) { .search-dropdown { position: relative; inset: auto; margin-top: 6px; } .search-control input { font-size: 16px; }.search-option { min-height: 48px; } }
</style>
