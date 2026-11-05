<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faChevronLeft, faChevronRight, faImages, faStore, faXmark } from "@fortawesome/free-solid-svg-icons"

const props = defineProps<{ images: string[], name: string }>()

// Kompyuterda: rasmlar soniga moslashadigan mozaika (5 tagacha), ortig'i "+N" bilan.
// Telefonda: suriladigan slayd-shou. Istalgan rasm bosilsa to'liq ekran galereya ochiladi.
const MOSAIC_LIMIT = 5
const mosaic = computed(() => props.images.slice(0, MOSAIC_LIMIT))
const hiddenCount = computed(() => Math.max(0, props.images.length - MOSAIC_LIMIT))
const layoutClass = computed(() => `count-${Math.min(props.images.length, MOSAIC_LIMIT)}`)

// --- Telefon slayd-shousi ---
const track = ref<HTMLElement | null>(null)
const slide = ref(0)
const onTrackScroll = () => {
  const el = track.value
  if (el?.clientWidth) slide.value = Math.round(el.scrollLeft / el.clientWidth)
}
const goToSlide = (index: number) => {
  track.value?.scrollTo({ left: index * (track.value?.clientWidth ?? 0), behavior: "smooth" })
}

// --- To'liq ekran galereya ---
const viewerOpen = ref(false)
const current = ref(0)
const closeButton = ref<HTMLButtonElement | null>(null)
let returnFocus: HTMLElement | null = null

const open = (index: number) => {
  returnFocus = document.activeElement as HTMLElement | null
  current.value = index
  viewerOpen.value = true
}
const close = () => { viewerOpen.value = false }
const step = (delta: number) => {
  const total = props.images.length
  current.value = (current.value + delta + total) % total
}

const onKeydown = (event: KeyboardEvent) => {
  if (!viewerOpen.value) return
  if (event.key === "Escape") close()
  else if (event.key === "ArrowRight") step(1)
  else if (event.key === "ArrowLeft") step(-1)
}

let touchX: number | null = null
const onTouchStart = (event: TouchEvent) => { touchX = event.touches[0]?.clientX ?? null }
const onTouchEnd = (event: TouchEvent) => {
  const endX = event.changedTouches[0]?.clientX
  if (touchX === null || endX === undefined) return
  const dx = endX - touchX
  if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1)
  touchX = null
}

watch(viewerOpen, async (isOpen) => {
  document.body.style.overflow = isOpen ? "hidden" : ""
  if (isOpen) {
    await nextTick()
    closeButton.value?.focus()
  } else {
    returnFocus?.focus()
  }
})
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown)
  document.body.style.overflow = ""
})
</script>

<template>
  <section class="branch-gallery" :aria-label="`${name} — rasmlar`">
    <!-- Rasm yo'q -->
    <div v-if="!images.length" class="gallery-empty">
      <FontAwesomeIcon :icon="faStore" />
    </div>

    <template v-else>
      <!-- Kompyuter: mozaika -->
      <div class="gallery-mosaic" :class="layoutClass">
        <button
          v-for="(img, idx) in mosaic"
          :key="`${idx}-${img}`"
          type="button"
          class="mosaic-tile"
          :aria-label="`${name}: ${idx + 1}-rasmni kattalashtirish`"
          @click="open(idx)"
        >
          <img :src="img" :alt="`${name} — ${idx + 1}`" :loading="idx === 0 ? 'eager' : 'lazy'">
          <span v-if="idx === mosaic.length - 1 && hiddenCount" class="more-overlay">+{{ hiddenCount }}</span>
        </button>
        <button v-if="images.length > 1" type="button" class="all-photos" @click="open(0)">
          <FontAwesomeIcon :icon="faImages" />
          <span>Barcha rasmlar ({{ images.length }})</span>
        </button>
      </div>

      <!-- Telefon: slayd-shou -->
      <div class="gallery-carousel">
        <div ref="track" class="carousel-track" @scroll.passive="onTrackScroll">
          <button
            v-for="(img, idx) in images"
            :key="`${idx}-${img}`"
            type="button"
            class="carousel-slide"
            :aria-label="`${name}: ${idx + 1}-rasmni kattalashtirish`"
            @click="open(idx)"
          >
            <img :src="img" :alt="`${name} — ${idx + 1}`" :loading="idx === 0 ? 'eager' : 'lazy'">
          </button>
        </div>
        <template v-if="images.length > 1">
          <span class="carousel-counter">{{ slide + 1 }} / {{ images.length }}</span>
          <div class="carousel-dots">
            <button
              v-for="(_, idx) in images"
              :key="idx"
              type="button"
              :class="{ active: idx === slide }"
              :aria-label="`${idx + 1}-rasm`"
              @click="goToSlide(idx)"
            />
          </div>
        </template>
      </div>
    </template>

    <!-- To'liq ekran galereya -->
    <Teleport to="body">
      <Transition name="viewer">
        <div
          v-if="viewerOpen"
          class="gallery-viewer"
          role="dialog"
          aria-modal="true"
          :aria-label="`${name} — rasmlar`"
          @click.self="close"
          @touchstart.passive="onTouchStart"
          @touchend.passive="onTouchEnd"
        >
          <div class="viewer-top">
            <span class="viewer-counter">{{ current + 1 }} / {{ images.length }}</span>
            <button ref="closeButton" type="button" class="viewer-btn" aria-label="Yopish" @click="close">
              <FontAwesomeIcon :icon="faXmark" />
            </button>
          </div>

          <div class="viewer-stage" @click.self="close">
            <button v-if="images.length > 1" type="button" class="viewer-btn viewer-nav prev" aria-label="Oldingi rasm" @click="step(-1)">
              <FontAwesomeIcon :icon="faChevronLeft" />
            </button>
            <Transition name="fade" mode="out-in">
              <img :key="current" :src="images[current]" :alt="`${name} — ${current + 1}`" class="viewer-image">
            </Transition>
            <button v-if="images.length > 1" type="button" class="viewer-btn viewer-nav next" aria-label="Keyingi rasm" @click="step(1)">
              <FontAwesomeIcon :icon="faChevronRight" />
            </button>
          </div>

          <div v-if="images.length > 1" class="viewer-strip">
            <button
              v-for="(img, idx) in images"
              :key="`${idx}-${img}`"
              type="button"
              :class="{ active: idx === current }"
              :aria-label="`${idx + 1}-rasm`"
              :aria-current="idx === current ? 'true' : undefined"
              @click="current = idx"
            >
              <img :src="img" alt="" loading="lazy">
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>
  </section>
</template>

<style scoped>
.branch-gallery { position: relative; }
.gallery-empty { display: grid; place-items: center; height: 320px; border-radius: 20px; background: var(--surface); color: var(--muted); font-size: 48px; }

/* ---------- Mozaika (kompyuter) ---------- */
.gallery-mosaic { position: relative; display: grid; gap: 8px; height: 440px; border-radius: 20px; overflow: hidden; }
.gallery-mosaic.count-1 { grid-template-columns: 1fr; }
.gallery-mosaic.count-2 { grid-template-columns: 1fr 1fr; }
.gallery-mosaic.count-3 { grid-template-columns: 2fr 1fr; grid-template-rows: 1fr 1fr; }
.gallery-mosaic.count-3 .mosaic-tile:first-child { grid-row: span 2; }
.gallery-mosaic.count-4 { grid-template-columns: 2fr 1fr 1fr; grid-template-rows: 1fr 1fr; }
.gallery-mosaic.count-4 .mosaic-tile:first-child { grid-row: span 2; }
.gallery-mosaic.count-4 .mosaic-tile:nth-child(2) { grid-column: span 2; }
.gallery-mosaic.count-5 { grid-template-columns: 2fr 1fr 1fr; grid-template-rows: 1fr 1fr; }
.gallery-mosaic.count-5 .mosaic-tile:first-child { grid-row: span 2; }

.mosaic-tile { position: relative; min-width: 0; min-height: 0; padding: 0; border: 0; background: #0f172a; cursor: zoom-in; overflow: hidden; }
.mosaic-tile img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .45s ease, filter .3s ease; }
.mosaic-tile:hover img { transform: scale(1.04); filter: brightness(1.06); }
.mosaic-tile:focus-visible { outline: 3px solid var(--accent); outline-offset: -3px; }
.more-overlay { position: absolute; inset: 0; display: grid; place-items: center; background: rgba(2, 6, 23, .55); color: #fff; font-size: 30px; font-weight: 800; letter-spacing: -.02em; }

.all-photos { position: absolute; right: 16px; bottom: 16px; display: inline-flex; align-items: center; gap: 8px; min-height: 40px; padding: 8px 16px; border: 1px solid rgba(255, 255, 255, .35); border-radius: 12px; background: rgba(2, 6, 23, .72); color: #fff; font: inherit; font-size: 13px; font-weight: 750; cursor: pointer; -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); box-shadow: 0 6px 18px rgba(0, 0, 0, .35); transition: background .2s; }
.all-photos:hover { background: rgba(2, 6, 23, .88); }
.all-photos:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }

/* ---------- Slayd-shou (telefon/planshet) ---------- */
.gallery-carousel { display: none; position: relative; border-radius: 16px; overflow: hidden; }
.carousel-track { display: flex; height: 280px; overflow-x: auto; scroll-snap-type: x mandatory; scrollbar-width: none; overscroll-behavior-x: contain; }
.carousel-track::-webkit-scrollbar { display: none; }
.carousel-slide { flex: 0 0 100%; padding: 0; border: 0; background: #0f172a; scroll-snap-align: start; cursor: zoom-in; }
.carousel-slide img { display: block; width: 100%; height: 100%; object-fit: cover; }
.carousel-counter { position: absolute; top: 12px; right: 12px; padding: 4px 10px; border-radius: 999px; background: rgba(2, 6, 23, .65); color: #fff; font-size: 12px; font-weight: 700; pointer-events: none; }
.carousel-dots { position: absolute; left: 0; right: 0; bottom: 10px; display: flex; justify-content: center; gap: 2px; }
.carousel-dots button { width: 22px; height: 22px; padding: 0; border: 0; background: transparent; cursor: pointer; }
.carousel-dots button::before { content: ""; display: block; width: 7px; height: 7px; margin: auto; border-radius: 50%; background: rgba(255, 255, 255, .55); box-shadow: 0 0 4px rgba(0, 0, 0, .4); transition: width .2s, background .2s; }
.carousel-dots button.active::before { width: 18px; border-radius: 4px; background: #fff; }

@media (max-width: 1024px) {
  .gallery-mosaic { display: none; }
  .gallery-carousel { display: block; }
}
@media (max-width: 768px) {
  .carousel-track { height: 230px; }
  .gallery-empty { height: 210px; border-radius: 14px; }
}

/* ---------- To'liq ekran galereya ---------- */
.gallery-viewer { position: fixed; inset: 0; z-index: 1000; display: grid; grid-template-rows: auto minmax(0, 1fr) auto; gap: 12px; padding: 16px; background: rgba(2, 6, 23, .94); -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); color: #fff; }
.viewer-top { display: flex; align-items: center; justify-content: space-between; }
.viewer-counter { font-size: 14px; font-weight: 700; opacity: .85; }
.viewer-stage { position: relative; display: grid; place-items: center; min-height: 0; }
.viewer-image { max-width: 100%; max-height: calc(100dvh - 190px); object-fit: contain; border-radius: 12px; box-shadow: 0 20px 60px rgba(0, 0, 0, .5); user-select: none; }
.viewer-btn { display: grid; place-items: center; width: 44px; height: 44px; padding: 0; border: 1px solid rgba(255, 255, 255, .25); border-radius: 50%; background: rgba(255, 255, 255, .1); color: #fff; font-size: 18px; cursor: pointer; transition: background .2s; }
.viewer-btn:hover { background: rgba(255, 255, 255, .22); }
.viewer-btn:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }
.viewer-nav { position: absolute; top: 50%; z-index: 1; transform: translateY(-50%); width: 52px; height: 52px; }
.viewer-nav.prev { left: 8px; }
.viewer-nav.next { right: 8px; }
.viewer-strip { display: flex; gap: 8px; overflow-x: auto; padding: 4px; scrollbar-width: thin; }
.viewer-strip button { flex: 0 0 auto; width: 72px; height: 52px; padding: 0; border: 2px solid transparent; border-radius: 8px; background: none; overflow: hidden; opacity: .5; cursor: pointer; transition: opacity .2s, border-color .2s; }
.viewer-strip button.active, .viewer-strip button:hover { opacity: 1; }
.viewer-strip button.active { border-color: #fff; }
/* Qisqa qatorda markazda, uzun qatorda boshidan suriladi (chetdagi rasm kesilmaydi). */
.viewer-strip button:first-child { margin-left: auto; }
.viewer-strip button:last-child { margin-right: auto; }
.viewer-strip img { display: block; width: 100%; height: 100%; object-fit: cover; }
@media (max-width: 768px) {
  .gallery-viewer { padding: 12px 8px; }
  .viewer-nav { display: none; }
  .viewer-strip button { width: 56px; height: 42px; }
  .viewer-image { max-height: calc(100dvh - 150px); }
}

.viewer-enter-active, .viewer-leave-active { transition: opacity .2s ease; }
.viewer-enter-from, .viewer-leave-to { opacity: 0; }
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .mosaic-tile img, .viewer-enter-active, .viewer-leave-active, .fade-enter-active, .fade-leave-active { transition: none; }
  .mosaic-tile:hover img { transform: none; }
}
</style>
