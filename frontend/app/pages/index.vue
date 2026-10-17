<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faLocationArrow } from "@fortawesome/free-solid-svg-icons"
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
</script>

<template>
  <div class="discovery-page">
    <section class="discovery-ad" aria-label="RezervUZ reklamasi">
      <div class="ad-copy">
        <span class="ad-eyebrow">REZERVUZ · SIZNING VAQTINGIZ QADRLI</span>
        <h1>Yaqin joy.<br>Qulay vaqt.<br><span>Hammasi bir joyda.</span></h1>
        <p>O‘yin klublari, sport zallari va sartaroshxonalar. O‘zingizga mos xizmatni toping va vaqtingizni oldindan bron qiling.</p>
        <div class="ad-benefits" aria-label="RezervUZ bilan qulayliklar">
          <span>Vaqtingizni tejang</span>
          <span>Uzoq kutmang</span>
          <span>Oldindan bron qiling</span>
        </div>
      </div>
      <div class="ad-art" aria-hidden="true">
        <div class="ad-orbit orbit-one" /><div class="ad-orbit orbit-two" />
        <div class="ad-pin">R<span>REZERVUZ</span></div>
        <span class="ad-tag tag-one">O‘ynang</span><span class="ad-tag tag-two">Dam oling</span><span class="ad-tag tag-three">Vaqtingizni bron qiling</span>
      </div>
      <span class="ad-label">Reklama</span>
    </section>

    <section class="discovery-nearby" aria-label="Yaqin xizmatlar xaritasi">
      <div class="map-workspace" :aria-busy="status === 'pending'">
        <div class="map-panel">
          <button type="button" class="map-locate" :disabled="locating" :aria-busy="locating" aria-label="Mening joylashuvim" title="Mening joylashuvim" @click="locate"><FontAwesomeIcon :icon="faLocationArrow" aria-hidden="true" /></button>
          <ClientOnly><DiscoveryNearbyMap :branches="branches" :location="location" :selected-id="selectedId" @select="selectedId = $event" /><template #fallback><div class="map-loading">Xarita yuklanmoqda…</div></template></ClientOnly>
          <div v-if="error" class="map-progress" role="alert">Xizmatlarni yuklab bo‘lmadi. <button type="button" @click="refresh()">Qayta urinish</button></div>
          <span v-else-if="status === 'pending'" class="map-progress" role="status">Xizmatlar yuklanmoqda…</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.discovery-page { display: grid; gap: 32px; padding-bottom: 24px; }
.discovery-ad { position: relative; display: grid; grid-template-columns: 1.15fr 1fr; align-items: center; min-height: clamp(340px, 46svh, 520px); overflow: hidden; padding: clamp(24px, 4vw, 56px); border-radius: 24px; background: radial-gradient(ellipse at 80% 25%, #5149a3 0, transparent 55%), linear-gradient(120deg, #14142b, #252154); color: white; }
.ad-copy { position: relative; z-index: 1; max-width: 540px; }
.ad-eyebrow { font-size: 10px; font-weight: 750; letter-spacing: .16em; }
.ad-eyebrow { color: #c4b5fd; }
h1 { margin: 18px 0; font-size: clamp(30px, 3.7vw, 56px); line-height: 1.08; letter-spacing: -.045em; }
h1 span { color: #bdb5ff; }
.ad-copy p { max-width: 390px; color: #d0cde7; font-size: 14px; line-height: 1.7; }
.ad-benefits { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }
.ad-benefits span { padding: 9px 12px; border: 1px solid #ffffff30; border-radius: 999px; background: #ffffff0d; color: #eeeaff; font-size: 12px; font-weight: 650; }
.ad-art { position: relative; min-height: 280px; display: grid; place-items: center; }
.ad-orbit { position: absolute; width: 260px; height: 260px; border: 1px solid #ffffff25; border-radius: 50%; transform: rotate(-25deg) scaleX(1.25); }
.orbit-two { width: 190px; height: 190px; transform: rotate(30deg) scaleX(1.3); }
.ad-pin { display: grid; place-content: center; gap: 4px; width: 140px; height: 160px; border: 1px solid #ffffff60; border-radius: 40px 40px 70px 70px; background: linear-gradient(135deg, #a89afa, #5044a6); box-shadow: 0 24px 80px #0005; font-size: 78px; font-weight: 900; text-align: center; transform: rotate(-8deg); }
.ad-pin span { font-size: 10px; letter-spacing: .12em; }
.ad-tag { position: absolute; padding: 10px 15px; border: 1px solid #ffffff30; border-radius: 12px; background: #ffffff15; backdrop-filter: blur(8px); font-size: 12px; }
.tag-one { top: 12px; left: 2%; transform: rotate(-10deg); }.tag-two { right: 0; top: 60px; transform: rotate(10deg); }.tag-three { bottom: 0; left: 12%; }
.ad-label { position: absolute; bottom: 14px; right: 18px; color: #ffffff80; font-size: 10px; }
.discovery-nearby { display: grid; gap: 16px; }
.locate-button { min-height: 44px; padding: 10px 16px; border: 1px solid var(--border); border-radius: 12px; background: var(--panel); color: var(--text); font: inherit; font-size: 13px; cursor: pointer; }.locate-button:disabled { opacity: .6; cursor: wait; }
.map-workspace { display: grid; grid-template-columns: minmax(0, 1fr); min-height: 440px; height: 55svh; max-height: 650px; overflow: hidden; border: 1px solid var(--border); border-radius: 20px; background: var(--panel); }
.map-panel { position: relative; min-width: 0; min-height: 0; }.map-loading { display: grid; place-items: center; height: 100%; min-height: 360px; color: var(--muted); }.map-progress { position: absolute; top: 12px; right: 12px; z-index: 1; padding: 10px; border-radius: 10px; background: var(--panel); color: var(--text); font-size: 12px; }
@media (max-width: 767px) {
  .discovery-page { gap: 14px; }
  .discovery-ad { grid-template-columns: 1fr; min-height: 0; border-radius: 16px; padding: 18px 18px 24px; }
  .ad-copy { max-width: 100%; }
  .ad-art, .ad-copy p { display: none; }
  .ad-eyebrow { display: block; font-size: 8px; letter-spacing: .1em; }
  h1 { margin: 10px 0 12px; font-size: clamp(23px, 6vw, 28px); line-height: 1.1; }
  .ad-benefits { gap: 5px; margin-top: 0; }
  .ad-benefits span { padding: 6px 8px; font-size: 10px; line-height: 1.3; }
  .ad-label { right: 12px; bottom: 7px; font-size: 8px; }
  .locate-button { width: 100%; }
  .map-workspace { display: flex; flex-direction: column; height: auto; max-height: none; }
  .map-panel { height: 48svh; min-height: 360px; }
}

.map-locate { position: absolute; z-index: 2; right: 12px; top: 12px; display: grid; place-items: center; width: 44px; height: 44px; border: 1px solid var(--border); border-radius: 12px; background: var(--panel); color: var(--text); font-size: 19px; cursor: pointer; box-shadow: 0 2px 8px #0002; }
.map-locate:disabled { opacity: .6; cursor: wait; }
.map-locate:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.map-progress { top: 66px; }
</style>
