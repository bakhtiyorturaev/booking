<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faChevronLeft, faChevronRight, faImages, faStore, faXmark } from "@fortawesome/free-solid-svg-icons"

const props = defineProps<{ images: string[], name: string }>()

// 3D "shisha" karusel: o'rtadagi rasm oldinda, yondagilari shisha ortida xiraroq.
// O'rtadagini bossa to'liq ekran galereya ochiladi, yondagisini bossa o'sha rasmga o'tadi.
const total = computed(() => props.images.length)
const active = ref(0)
const VISIBLE_SIDE = 2
const AUTOPLAY_MS = 5000

// Aylanma masofa: oxirgi rasmdan keyin birinchisi keladi.
const offsetOf = (idx: number) => {
  const n = total.value
  let d = idx - active.value
  if (d > n / 2) d -= n
  if (d < -n / 2) d += n
  return d
}
const slideStyle = (idx: number) => {
  const d = offsetOf(idx)
  const abs = Math.abs(d)
  return {
    "--d": d,
    "--abs": abs,
    zIndex: 10 - abs,
    opacity: abs > VISIBLE_SIDE ? 0 : 1,
    pointerEvents: abs > VISIBLE_SIDE ? "none" as const : undefined,
  }
}
const go = (delta: number) => {
  const n = total.value
  if (n > 1) active.value = (active.value + delta + n) % n
}
const onSlideClick = (idx: number) => {
  if (offsetOf(idx) === 0) open(idx)
  else active.value = idx
}

// Avtomatik aylanish: sichqoncha ustida, fokusda, galereya ochiq yoki "kamroq harakat" yoqilgan bo'lsa to'xtaydi.
const paused = ref(false)
let timer: ReturnType<typeof setInterval> | null = null
const stopAutoplay = () => { if (timer) clearInterval(timer); timer = null }
const startAutoplay = () => {
  stopAutoplay()
  if (total.value < 2 || matchMedia("(prefers-reduced-motion: reduce)").matches) return
  timer = setInterval(() => {
    if (!paused.value && !viewerOpen.value && !document.hidden) go(1)
  }, AUTOPLAY_MS)
}

let stageTouchX: number | null = null
const onStageTouchStart = (event: TouchEvent) => { stageTouchX = event.touches[0]?.clientX ?? null; paused.value = true }
const onStageTouchEnd = (event: TouchEvent) => {
  const endX = event.changedTouches[0]?.clientX
  if (stageTouchX !== null && endX !== undefined && Math.abs(endX - stageTouchX) > 40) go(endX < stageTouchX ? 1 : -1)
  stageTouchX = null
  paused.value = false
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
const close = () => {
  viewerOpen.value = false
  active.value = current.value
}
const step = (delta: number) => {
  const n = total.value
  current.value = (current.value + delta + n) % n
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
watch(total, () => { active.value = 0; startAutoplay() })
onMounted(() => {
  window.addEventListener("keydown", onKeydown)
  startAutoplay()
})
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown)
  stopAutoplay()
  document.body.style.overflow = ""
})
</script>

<template>
  <section class="branch-gallery" :aria-label="`${name} — rasmlar`">
    <div v-if="!images.length" class="gallery-empty">
      <FontAwesomeIcon :icon="faStore" />
    </div>

    <div
      v-else
      class="glass-stage"
      :class="{ single: total === 1 }"
      aria-roledescription="karusel"
      @mouseenter="paused = true"
      @mouseleave="paused = false"
      @focusin="paused = true"
      @focusout="paused = false"
      @touchstart.passive="onStageTouchStart"
      @touchend.passive="onStageTouchEnd"
    >
      <!-- Faol rasmning xiralashtirilgan foni -->
      <Transition name="fade">
        <div :key="active" class="stage-backdrop" :style="{ backgroundImage: `url('${images[active]}')` }" aria-hidden="true" />
      </Transition>

      <div class="stage-track">
        <button
          v-for="(img, idx) in images"
          :key="`${idx}-${img}`"
          type="button"
          class="glass-slide"
          :class="{ center: offsetOf(idx) === 0 }"
          :style="slideStyle(idx)"
          :tabindex="Math.abs(offsetOf(idx)) > 1 ? -1 : 0"
          :aria-label="offsetOf(idx) === 0 ? `${name}: ${idx + 1}-rasmni kattalashtirish` : `${idx + 1}-rasmga o'tish`"
          :aria-current="offsetOf(idx) === 0 ? 'true' : undefined"
          @click="onSlideClick(idx)"
        >
          <img :src="img" :alt="`${name} — ${idx + 1}`" :loading="Math.abs(offsetOf(idx)) <= 1 ? 'eager' : 'lazy'" draggable="false">
        </button>
      </div>

      <template v-if="total > 1">
        <button type="button" class="glass-btn stage-nav prev" aria-label="Oldingi rasm" @click="go(-1)">
          <FontAwesomeIcon :icon="faChevronLeft" />
        </button>
        <button type="button" class="glass-btn stage-nav next" aria-label="Keyingi rasm" @click="go(1)">
          <FontAwesomeIcon :icon="faChevronRight" />
        </button>
        <div class="stage-dots">
          <button
            v-for="(_, idx) in images"
            :key="idx"
            type="button"
            :class="{ active: idx === active }"
            :aria-label="`${idx + 1}-rasm`"
            @click="active = idx"
          />
        </div>
      </template>
      <span class="glass-pill stage-counter" aria-live="polite">{{ active + 1 }} / {{ total }}</span>
      <button type="button" class="glass-pill stage-all" @click="open(active)">
        <FontAwesomeIcon :icon="faImages" />
        <span>Barcha rasmlar</span>
      </button>
    </div>

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
            <span class="viewer-counter">{{ current + 1 }} / {{ total }}</span>
            <button ref="closeButton" type="button" class="viewer-btn" aria-label="Yopish" @click="close">
              <FontAwesomeIcon :icon="faXmark" />
            </button>
          </div>

          <div class="viewer-stage" @click.self="close">
            <button v-if="total > 1" type="button" class="viewer-btn viewer-nav prev" aria-label="Oldingi rasm" @click="step(-1)">
              <FontAwesomeIcon :icon="faChevronLeft" />
            </button>
            <Transition name="fade" mode="out-in">
              <img :key="current" :src="images[current]" :alt="`${name} — ${current + 1}`" class="viewer-image">
            </Transition>
            <button v-if="total > 1" type="button" class="viewer-btn viewer-nav next" aria-label="Keyingi rasm" @click="step(1)">
              <FontAwesomeIcon :icon="faChevronRight" />
            </button>
          </div>

          <div v-if="total > 1" class="viewer-strip">
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
.gallery-empty { display: grid; place-items: center; height: 320px; border-radius: 24px; background: var(--surface); color: var(--muted); font-size: 48px; }

/* ---------- 3D shisha karusel ---------- */
.glass-stage {
  --slide-w: 58%;
  --shift: 52%;
  position: relative;
  height: 440px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, .35);
  border-radius: 24px;
  background: #0b1220;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .35), 0 18px 40px rgba(2, 6, 23, .18);
  isolation: isolate;
  user-select: none;
}
.stage-backdrop { position: absolute; inset: -40px; z-index: -1; background-position: center; background-size: cover; filter: blur(34px) saturate(150%) brightness(.75); transform: scale(1.1); }
.stage-backdrop::after { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(255, 255, 255, .08), rgba(2, 6, 23, .25)); }

.stage-track { position: absolute; inset: 0; perspective: 1400px; }
.glass-slide {
  position: absolute;
  top: 8%;
  left: calc((100% - var(--slide-w)) / 2);
  width: var(--slide-w);
  height: 84%;
  padding: 0;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, .45);
  border-radius: 20px;
  background: rgba(255, 255, 255, .08);
  cursor: pointer;
  transform:
    translateX(calc(var(--d) * var(--shift)))
    scale(calc(1 - var(--abs) * .16))
    rotateY(calc(var(--d) * -14deg));
  box-shadow: 0 24px 50px rgba(2, 6, 23, .45), inset 0 1px 0 rgba(255, 255, 255, .5);
  transition: transform .6s cubic-bezier(.22, .8, .25, 1), opacity .5s ease, filter .5s ease;
  filter: saturate(calc(1 - var(--abs) * .25));
}
.glass-slide img { display: block; width: 100%; height: 100%; object-fit: cover; pointer-events: none; }
/* Yon rasmlar ustidagi shisha qatlam */
.glass-slide::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, .28), rgba(255, 255, 255, .06) 45%, rgba(255, 255, 255, .14));
  -webkit-backdrop-filter: blur(3px);
  backdrop-filter: blur(3px);
  transition: opacity .5s ease;
}
.glass-slide.center { cursor: zoom-in; }
.glass-slide.center::after { opacity: 0; }
/* Faol rasmdagi nozik yaltiroq chiziq */
.glass-slide.center::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: inherit;
  background: linear-gradient(120deg, rgba(255, 255, 255, .22), transparent 30%);
  pointer-events: none;
}
.glass-slide:focus-visible { outline: 3px solid #fff; outline-offset: 3px; }

.glass-stage.single { --slide-w: 86%; }

.glass-btn, .glass-pill {
  border: 1px solid rgba(255, 255, 255, .4);
  background: rgba(15, 23, 42, .38);
  color: #fff;
  -webkit-backdrop-filter: blur(14px) saturate(160%);
  backdrop-filter: blur(14px) saturate(160%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .45), 0 8px 20px rgba(2, 6, 23, .25);
}
.glass-btn { display: grid; place-items: center; width: 46px; height: 46px; padding: 0; border-radius: 50%; font-size: 17px; cursor: pointer; transition: background .2s, transform .2s; }
.glass-btn:hover { background: rgba(15, 23, 42, .55); transform: translateY(-50%) scale(1.06); }
.glass-btn:focus-visible, .glass-pill:focus-visible, .stage-dots button:focus-visible { outline: 2px solid #fff; outline-offset: 2px; }
.stage-nav { position: absolute; top: 50%; z-index: 20; transform: translateY(-50%); }
.stage-nav.prev { left: 16px; }
.stage-nav.next { right: 16px; }

.glass-pill { display: inline-flex; align-items: center; gap: 8px; min-height: 36px; padding: 6px 14px; border-radius: 999px; font: inherit; font-size: 13px; font-weight: 700; }
.stage-counter { position: absolute; top: 14px; right: 14px; z-index: 20; pointer-events: none; }
.stage-all { position: absolute; right: 14px; bottom: 14px; z-index: 20; cursor: pointer; transition: background .2s; }
.stage-all:hover { background: rgba(15, 23, 42, .55); }

.stage-dots { position: absolute; left: 50%; bottom: 14px; z-index: 20; display: flex; gap: 2px; padding: 4px 8px; border-radius: 999px; background: rgba(2, 6, 23, .25); transform: translateX(-50%); -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(10px); }
.stage-dots button { width: 20px; height: 20px; padding: 0; border: 0; background: transparent; cursor: pointer; }
.stage-dots button::before { content: ""; display: block; width: 7px; height: 7px; margin: auto; border-radius: 50%; background: rgba(255, 255, 255, .55); transition: width .25s, background .25s; }
.stage-dots button.active::before { width: 18px; border-radius: 4px; background: #fff; }

@media (max-width: 1024px) {
  .glass-stage { --slide-w: 66%; --shift: 50%; height: 340px; }
}
@media (max-width: 768px) {
  .glass-stage { --slide-w: 74%; --shift: 46%; height: 260px; border-radius: 18px; }
  .glass-slide { border-radius: 14px; }
  .stage-nav { display: none; }
  .stage-all span { display: none; }
  .stage-all { min-height: 34px; padding: 6px 10px; }
  .stage-dots { bottom: 10px; }
  .stage-counter { top: 10px; right: 10px; min-height: 30px; padding: 4px 10px; font-size: 12px; }
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
.fade-enter-active, .fade-leave-active { transition: opacity .35s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .glass-slide, .glass-slide::after, .viewer-enter-active, .viewer-leave-active, .fade-enter-active, .fade-leave-active { transition: none; }
}
</style>
