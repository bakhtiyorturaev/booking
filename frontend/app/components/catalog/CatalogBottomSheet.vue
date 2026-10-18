<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  title: string
  sheetClass?: string
}>()

const emit = defineEmits<{ (event: "update:modelValue", value: boolean): void }>()
const titleId = useId()
const dialog = ref<HTMLElement | null>(null)
let previousFocus: HTMLElement | null = null
let previousOverflow = ""

const close = () => emit("update:modelValue", false)

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === "Escape") {
    event.preventDefault()
    close()
    return
  }
  if (event.key !== "Tab" || !dialog.value) return
  const focusable = [...dialog.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex="0"]',
  )]
  if (!focusable.length) {
    event.preventDefault()
    dialog.value.focus()
    return
  }
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (!first || !last) return
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(() => props.modelValue, async (open) => {
  if (!import.meta.client) return
  if (open) {
    previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    window.addEventListener("keydown", onKeydown)
    await nextTick()
    dialog.value?.focus()
  } else {
    document.body.style.overflow = previousOverflow
    window.removeEventListener("keydown", onKeydown)
    await nextTick()
    previousFocus?.focus()
  }
}, { immediate: true })

onBeforeUnmount(() => {
  if (!import.meta.client) return
  document.body.style.overflow = previousOverflow
  window.removeEventListener("keydown", onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="catalog-sheet">
      <div v-if="modelValue" class="sheet-backdrop" @click.self="close">
        <section
          ref="dialog"
          class="sheet-panel glass-panel"
          :class="sheetClass"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
        >
          <div class="sheet-grabber" aria-hidden="true"><span /></div>
          <header class="sheet-header">
            <h2 :id="titleId">{{ title }}</h2>
            <button class="sheet-close" type="button" aria-label="Yopish" @click="close">×</button>
          </header>
          <div class="sheet-content"><slot /></div>
          <slot name="footer" />
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.sheet-backdrop {
  position: fixed;
  z-index: 1200;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-top: max(12px, env(safe-area-inset-top));
  background: rgb(15 23 42 / 48%);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
}
.sheet-panel {
  width: min(100%, 680px);
  max-height: min(84dvh, 820px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-bottom: 0;
  border-radius: 22px 22px 0 0;
  color: var(--text, #172033);
  box-shadow: 0 -16px 48px rgb(15 23 42 / 18%);
  outline: none;
  padding-bottom: env(safe-area-inset-bottom);
}
.sheet-grabber { display: flex; justify-content: center; padding: 10px 0 2px; flex: 0 0 auto; }
.sheet-grabber span { width: 38px; height: 4px; border-radius: 999px; background: var(--muted, #94a3b8); opacity: .48; }
.sheet-header { min-height: 54px; padding: 4px 18px 12px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--border, #e2e8f0); }
.sheet-header h2 { margin: 0; font-size: 18px; line-height: 1.25; font-weight: 800; }
.sheet-close { width: 44px; height: 44px; display: grid; place-items: center; border: 1px solid var(--border, #e2e8f0); border-radius: 50%; background: transparent; color: var(--text, #172033); font-size: 25px; line-height: 1; cursor: pointer; }
.sheet-content { min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
.catalog-sheet-enter-active, .catalog-sheet-leave-active { transition: opacity .2s ease; }
.catalog-sheet-enter-active .sheet-panel, .catalog-sheet-leave-active .sheet-panel { transition: transform .24s cubic-bezier(.2,.8,.2,1); }
.catalog-sheet-enter-from, .catalog-sheet-leave-to { opacity: 0; }
.catalog-sheet-enter-from .sheet-panel, .catalog-sheet-leave-to .sheet-panel { transform: translateY(40px); }
@media (min-width: 700px) {
  .sheet-backdrop { align-items: center; padding: 24px; }
  .sheet-panel { border-bottom: 1px solid var(--border, #e2e8f0); border-radius: 20px; }
}
</style>
