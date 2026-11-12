<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faArrowRight, faLocationArrow, faMagnifyingGlass, faScissors } from "@fortawesome/free-solid-svg-icons"
import { useBranchesApi } from "~/api/branches"
import type { BranchListSummary } from "~/types/club"

definePageMeta({ layout: "customer" })
useHead({ title: "RezervUZ — Yaqin xizmatlarni toping" })
const branchesApi = useBranchesApi()
const location = ref<{ latitude: number; longitude: number } | null>(null)
const locating = ref(false)
const selectedId = ref<string | null>(null)
const { data: result, status, error, refresh } = await useAsyncData("home-map-branches", () => branchesApi.list({
  ...(location.value ? { ...location.value, ordering: "distance" } : { ordering: "-rating" }),
}), { watch: [location] })
const branches = computed<BranchListSummary[]>(() => (result.value?.results || []).filter(branch => {
  if (branch.latitude == null || branch.longitude == null || branch.latitude === "" || branch.longitude === "") return false
  return Number.isFinite(Number(branch.latitude)) && Number.isFinite(Number(branch.longitude))
    && Math.abs(Number(branch.latitude)) <= 90 && Math.abs(Number(branch.longitude)) <= 180
}))
watch(branches, () => { selectedId.value = null })
const locate = () => {
  if (locating.value) return
  if (!navigator.geolocation) return
  locating.value = true
  navigator.geolocation.getCurrentPosition(position => {
    location.value = { latitude: position.coords.latitude, longitude: position.coords.longitude }
    locating.value = false
  }, () => {
    locating.value = false
  }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 })
}
onMounted(locate)

// Qidiruv katalogga ?q= bilan o'tadi; katalog uni filtrdagi qidiruv maydoniga qo'yadi.
const query = ref("")
const search = () => {
  const q = query.value.trim()
  void navigateTo({ path: "/catalog", query: q ? { q } : {} })
}

// Bento-to'r: xizmat turlari. Kodlar backend'dagi ServiceType.code bilan bir xil.
const categories = [
  { code: "COMPUTER", title: "Kompyuter klublari", subtitle: "Oddiy, VIP va turnir xonalari", image: "/images/categories/computer.webp", size: "large" },
  { code: "PLAYSTATION", title: "PlayStation", subtitle: "PS5 xonalari do‘stlar bilan", image: "/images/categories/playstation.webp", size: "wide" },
  { code: "BILLIARDS", title: "Bilyard", subtitle: "Rus va amerikan pul", image: "/images/categories/billiards.webp", size: "small" },
  { code: "BARBERSHOP", title: "Sartaroshlar", subtitle: "Erkak va ayol ustalar", image: null, size: "small" },
] as const
</script>

<template>
  <div class="discovery-page">
    <section class="home-hero" aria-labelledby="home-title">
      <span class="hero-chip"><span class="live-dot" aria-hidden="true" />Bo‘sh vaqtlar onlayn</span>
      <h1 id="home-title">O‘yin va dam olish —<br><span class="hero-gradient">bir bosishda bron.</span></h1>
      <p class="hero-lead">Kompyuter klublari, PlayStation, bilyard va sartaroshlar. Joyni tanlang, vaqtni belgilang — tasdiq Telegram’ga keladi.</p>
      <form class="hero-search" role="search" @submit.prevent="search">
        <label for="home-search" class="sr-only">Qidirish</label>
        <FontAwesomeIcon :icon="faMagnifyingGlass" class="hero-search-icon" aria-hidden="true" />
        <input id="home-search" v-model="query" type="search" placeholder="Klub, usta yoki manzil" autocomplete="off" enterkeyhint="search">
        <button type="submit" class="cta-button">Topish</button>
      </form>
    </section>

    <nav class="home-bento" aria-label="Xizmat turlari">
      <NuxtLink
        v-for="item in categories"
        :key="item.code"
        :to="{ path: '/catalog', query: { service: item.code } }"
        class="bento-tile"
        :class="[`bento-${item.size}`, { 'bento-accent': !item.image }]"
      >
        <img v-if="item.image" :src="item.image" alt="" class="bento-img" :loading="item.size === 'large' ? 'eager' : 'lazy'">
        <span v-else class="bento-icon" aria-hidden="true"><FontAwesomeIcon :icon="faScissors" /></span>
        <span class="bento-text">
          <span class="bento-title">{{ item.title }}</span>
          <span class="bento-subtitle">{{ item.subtitle }}</span>
        </span>
        <span v-if="item.size === 'large'" class="bento-arrow" aria-hidden="true"><FontAwesomeIcon :icon="faArrowRight" /></span>
      </NuxtLink>
    </nav>

    <section id="xarita" class="discovery-nearby" aria-labelledby="map-title">
      <div class="section-head">
        <h2 id="map-title">Xaritada</h2>
        <NuxtLink to="/catalog" class="section-link">Barchasi <FontAwesomeIcon :icon="faArrowRight" aria-hidden="true" /></NuxtLink>
      </div>
      <div class="map-workspace" :aria-busy="status === 'pending'">
        <div class="map-panel">
          <button type="button" class="map-locate" :disabled="locating" :aria-busy="locating" aria-label="Mening joylashuvim" title="Mening joylashuvim" @click="locate"><FontAwesomeIcon :icon="faLocationArrow" aria-hidden="true" /></button>
          <ClientOnly><DiscoveryNearbyMap :branches="branches" :location="location" :selected-id="selectedId" @select="selectedId = $event" /><template #fallback><div class="map-loading">Xarita yuklanmoqda…</div></template></ClientOnly>
          <div v-if="error" class="map-progress" role="alert">Xizmatlarni yuklab bo‘lmadi. <button type="button" @click="refresh()">Qayta urinish</button></div>
          <span v-else-if="status === 'pending'" class="map-progress" role="status">Xizmatlar yuklanmoqda…</span>
        </div>
      </div>
    </section>

    <section class="how-it-works" aria-label="Qanday ishlaydi">
      <div class="how-step"><span class="how-num">01</span><strong>Joyni tanlang</strong><span>Klub, xona yoki ustani katalog yoki xaritadan toping.</span></div>
      <div class="how-step"><span class="how-num">02</span><strong>Vaqtni belgilang</strong><span>Bo‘sh soatlar ko‘rinib turadi — qulayini bosing.</span></div>
      <div class="how-step"><span class="how-num">03</span><strong>Telegram’da tasdiq</strong><span>Tasdiqlangach, manzil va xarita havolasi keladi.</span></div>
    </section>
  </div>
</template>

<style scoped>
.discovery-page { display: flex; flex-direction: column; gap: 40px; padding: 12px 0 32px; }

/* ---------- Hero ---------- */
.home-hero { display: flex; flex-direction: column; align-items: center; gap: 20px; padding: 28px 0 4px; text-align: center; }
.hero-chip { display: inline-flex; align-items: center; gap: 8px; min-height: 34px; padding: 0 14px; border: 1px solid var(--glass-border); border-radius: 999px; background: var(--glass); color: var(--muted); font-size: 14px; font-weight: 700; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #34d399; box-shadow: 0 0 10px #34d399; }
.home-hero h1 { max-width: 920px; margin: 0; font-size: clamp(32px, 5.4vw, 68px); line-height: 1.04; font-weight: 800; letter-spacing: -0.035em; }
.hero-gradient { background: linear-gradient(90deg, #b7aeff, #7cc8ff 55%, #6ee7b7); -webkit-background-clip: text; background-clip: text; color: transparent; }
:root[data-theme="light"] .hero-gradient { background-image: linear-gradient(90deg, #5b3ff0, #1d6fe0 55%, #0f8f68); }
.hero-lead { max-width: 600px; margin: 0; color: var(--muted); font-size: clamp(16px, 1.6vw, 19px); line-height: 1.6; }
.hero-search { position: relative; display: flex; align-items: center; gap: 8px; width: 100%; max-width: 680px; margin-top: 6px; padding: 8px 8px 8px 50px; border: 1px solid var(--glass-border); border-radius: 22px; background: var(--glass); box-shadow: 0 24px 70px rgba(124, 92, 255, 0.22); -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px); }
.hero-search-icon { position: absolute; left: 20px; color: var(--muted); font-size: 18px; }
.hero-search input { flex: 1; min-width: 0; height: 48px; border: 0; outline: 0; background: none; color: var(--text); font-size: 17px; }
.hero-search input::placeholder { color: var(--muted); }
.hero-search:focus-within { border-color: var(--accent); }
.cta-button { flex-shrink: 0; min-height: 48px; padding: 0 26px; border: 0; border-radius: 16px; background: var(--cta); color: #fff; font-size: 16px; font-weight: 800; cursor: pointer; box-shadow: var(--cta-glow); transition: transform .2s, filter .2s; }
.cta-button:hover { filter: brightness(1.08); transform: translateY(-1px); }
.cta-button:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }

/* ---------- Bento ---------- */
.home-bento { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-template-rows: 220px 220px; gap: 14px; }
.bento-tile { position: relative; display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; padding: 22px; overflow: hidden; border: 1px solid var(--glass-border); border-radius: 28px; background: #12121c; color: #fff; text-decoration: none; isolation: isolate; transition: transform .25s ease, box-shadow .25s ease; }
.bento-tile:hover { transform: translateY(-3px); box-shadow: 0 20px 44px rgba(0, 0, 0, 0.35); }
.bento-tile:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
.bento-large { grid-column: span 2; grid-row: span 2; padding: 28px; }
.bento-wide { grid-column: span 2; }
.bento-img { position: absolute; inset: 0; z-index: -2; width: 100%; height: 100%; object-fit: cover; transition: transform .5s ease; }
.bento-tile:hover .bento-img { transform: scale(1.05); }
.bento-tile:has(.bento-img)::before { content: ""; position: absolute; inset: 0; z-index: -1; background: linear-gradient(180deg, rgba(7, 7, 13, 0) 35%, rgba(7, 7, 13, 0.88) 100%); }
.bento-wide:has(.bento-img)::before { background: linear-gradient(90deg, rgba(7, 7, 13, 0.85) 0%, rgba(7, 7, 13, 0.1) 75%); }
.bento-accent { flex-direction: column; align-items: flex-start; background: linear-gradient(140deg, #ff7a59 0%, #e0457b 60%, #7c5cff 130%); border-color: rgba(255, 255, 255, 0.2); }
.bento-icon { font-size: 30px; }
.bento-text { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.bento-title { font-family: var(--font-display); font-size: 21px; font-weight: 800; line-height: 1.15; }
.bento-large .bento-title { font-size: clamp(24px, 2.6vw, 34px); }
.bento-wide .bento-title { font-size: 25px; }
.bento-subtitle { color: rgba(255, 255, 255, 0.82); font-size: 15px; font-weight: 600; }
.bento-arrow { display: grid; place-items: center; flex-shrink: 0; width: 54px; height: 54px; border-radius: 50%; background: #fff; color: #07070d; font-size: 18px; transform: rotate(-45deg); }

/* ---------- Bo'lim sarlavhasi ---------- */
.section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; }
.section-head h2 { margin: 0; font-family: var(--font-display); font-size: clamp(22px, 2.4vw, 30px); font-weight: 800; letter-spacing: -0.02em; }
.section-link { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 16px; border: 1px solid var(--glass-border); border-radius: 14px; background: var(--glass); color: var(--text); font-size: 15px; font-weight: 700; text-decoration: none; }
.section-link:hover { border-color: var(--accent); }

/* ---------- Xarita ---------- */
.discovery-nearby { display: flex; flex-direction: column; gap: 16px; }
.map-workspace { display: grid; grid-template-columns: minmax(0, 1fr); height: 440px; overflow: hidden; border: 1px solid var(--glass-border); border-radius: 28px; background: var(--panel); }
.map-panel { position: relative; min-width: 0; min-height: 0; }
.map-loading { display: grid; place-items: center; height: 100%; min-height: 240px; color: var(--muted); }
.map-progress { position: absolute; top: 66px; right: 12px; z-index: 1; padding: 10px; border-radius: 10px; background: var(--panel); color: var(--text); font-size: 13px; }
.map-locate { position: absolute; z-index: 2; right: 12px; top: 12px; display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid var(--border); border-radius: 14px; background: var(--panel); color: var(--text); font-size: 19px; cursor: pointer; box-shadow: 0 2px 8px #0002; }
.map-locate:disabled { opacity: .6; cursor: wait; }
.map-locate:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* ---------- Qanday ishlaydi ---------- */
.how-it-works { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.how-step { display: flex; flex-direction: column; gap: 10px; padding: 24px; border: 1px solid var(--glass-border); border-radius: 24px; background: var(--glass); }
.how-step strong { font-size: 18px; }
.how-step > span:last-child { color: var(--muted); font-size: 15px; line-height: 1.55; }
.how-num { font-family: var(--font-display); font-size: 34px; font-weight: 800; color: #b7aeff; }
.how-step:nth-child(2) .how-num { color: #7cc8ff; }
.how-step:nth-child(3) .how-num { color: #6ee7b7; }
:root[data-theme="light"] .how-num { color: #5b3ff0; }
:root[data-theme="light"] .how-step:nth-child(2) .how-num { color: #1d6fe0; }
:root[data-theme="light"] .how-step:nth-child(3) .how-num { color: #0f8f68; }

@media (max-width: 1024px) {
  .home-bento { grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: 200px 150px 150px; }
  .bento-large { grid-row: span 1; }
  .bento-wide { grid-column: span 1; }
}
@media (max-width: 767px) {
  .discovery-page { gap: 28px; padding-top: 4px; }
  .home-hero { align-items: flex-start; padding-top: 12px; text-align: left; gap: 14px; }
  .home-hero h1 { font-size: clamp(26px, 7.4vw, 32px); }
  .hero-lead { font-size: 15px; }
  .hero-search { padding-left: 44px; border-radius: 18px; }
  .hero-search-icon { left: 16px; }
  .hero-search input { height: 44px; font-size: 16px; }
  .cta-button { min-height: 44px; padding: 0 18px; font-size: 15px; }
  .home-bento { grid-template-rows: 170px 120px 120px; gap: 10px; }
  .bento-large { grid-column: span 2; padding: 18px; }
  .bento-tile { padding: 14px; border-radius: 22px; }
  .bento-title, .bento-wide .bento-title { font-size: 16px; }
  .bento-large .bento-title { font-size: 22px; }
  .bento-subtitle { font-size: 13px; }
  .bento-small .bento-subtitle, .bento-wide .bento-subtitle { display: none; }
  .bento-arrow { width: 44px; height: 44px; font-size: 16px; }
  .bento-icon { font-size: 24px; }
  .map-workspace { height: 52svh; min-height: 340px; border-radius: 22px; }
  .how-it-works { grid-template-columns: 1fr; }
  .how-step { padding: 18px; }
}
@media (prefers-reduced-motion: reduce) {
  .bento-tile, .bento-img, .cta-button { transition: none; }
  .bento-tile:hover, .bento-tile:hover .bento-img { transform: none; }
}
</style>
