<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import L from "leaflet"
import { icon, type IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { faGamepad, faDesktop, faScissors, faDumbbell, faFutbol, faBuilding, faStore, faPerson, faCircleDot } from "@fortawesome/free-solid-svg-icons"
import type { BranchListSummary } from "~/types/club"

const props = defineProps<{
  branches: BranchListSummary[]
  location: { latitude: number; longitude: number } | null
  selectedId: string | null
}>()
const emit = defineEmits<{ select: [id: string] }>()
const container = ref<HTMLDivElement | null>(null)
const tileError = ref(false)
let map: L.Map | null = null
let layer: L.LayerGroup | null = null
let observer: ResizeObserver | null = null
const markers = new Map<string, L.Marker>()
const serviceSymbol = (branch: BranchListSummary): { symbol: IconDefinition; color: string } => {
  const service = [branch.club.category, branch.club.service_name, ...branch.service_types].join(" ").toUpperCase()
  if (/BARBER|SALON|SARTAROSH|HAIR/.test(service)) return { symbol: faScissors, color: "#db2777" }
  if (/GYM|FITNESS|SPORT|TRENAJ|ФИТНЕС/.test(service)) return { symbol: faDumbbell, color: "#059669" }
  if (/FOOTBALL|FUTBOL|STADIUM|ФУТБОЛ/.test(service)) return { symbol: faFutbol, color: "#16a34a" }
  if (/BILLIARD|BILYARD|БИЛЬЯРД/.test(service)) return { symbol: faCircleDot, color: "#0f766e" }
  if (/PLAYSTATION|CONSOLE|PS[45]/.test(service)) return { symbol: faGamepad, color: "#7c3aed" }
  if (/COMPUTER|CYBER|PC|KOMPYUTER/.test(service)) return { symbol: faDesktop, color: "#4f46e5" }
  if (/GAMING|GAME|O‘YIN|O'YIN/.test(service)) return { symbol: faGamepad, color: "#7c3aed" }
  if (/HALL|EVENT|ZAL|TO‘Y|TO'Y/.test(service)) return { symbol: faBuilding, color: "#d97706" }
  return { symbol: faStore, color: "#475569" }
}
const serviceIcon = (branch: BranchListSummary) => {
  const { symbol, color } = serviceSymbol(branch)
  const badge = document.createElement("span")
  badge.className = "service-map-badge"
  badge.style.setProperty("--marker-color", color)
  badge.innerHTML = icon(symbol).html.join("")
  return L.divIcon({ html: badge, className: "service-map-marker", iconSize: [40, 48], iconAnchor: [20, 48], popupAnchor: [0, -44], tooltipAnchor: [0, -42] })
}
const render = () => {
  if (!map || !layer) return
  layer.clearLayers()
  markers.clear()
  const points: L.LatLngExpression[] = []
  for (const branch of props.branches) {
    if (branch.latitude == null || branch.longitude == null || branch.latitude === "" || branch.longitude === "") continue
    const lat = Number(branch.latitude)
    const lng = Number(branch.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) continue
    const point: L.LatLngExpression = [lat, lng]
    points.push(point)
    const popup = document.createElement("div")
    const title = document.createElement("strong")
    title.textContent = `${branch.club.name} — ${branch.name}`
    const address = document.createElement("p")
    address.textContent = branch.full_address || branch.address
    const link = document.createElement("a")
    link.href = `/branches/${encodeURIComponent(branch.id)}`
    link.textContent = "Ko‘rish va bron qilish →"
    popup.append(title, address, link)
    const marker = L.marker(point, { icon: serviceIcon(branch), title: `${branch.club.name} — ${branch.name}`, alt: branch.club.name, riseOnHover: true })
      .bindTooltip(branch.club.name, { direction: "top" })
      .bindPopup(popup).on("click", () => emit("select", branch.id)).addTo(layer)
    markers.set(branch.id, marker)
  }
  if (props.location) {
    const point: L.LatLngExpression = [props.location.latitude, props.location.longitude]
    const userBadge = document.createElement("span")
    userBadge.className = "user-map-badge"
    userBadge.innerHTML = icon(faPerson).html.join("")
    L.marker(point, {
      icon: L.divIcon({ html: userBadge, className: "user-map-marker", iconSize: [48, 48], iconAnchor: [24, 24], tooltipAnchor: [0, 30] }),
      title: "Sizning joylashuvingiz", alt: "Sizning joylashuvingiz", zIndexOffset: 1000,
    }).bindTooltip("Siz shu yerdasiz", { permanent: true, direction: "bottom", className: "user-map-label" }).addTo(layer)
  }
  // Keep the user's location close even when distant service markers load.
  if (props.location) {
    map.stop()
    map.setView([props.location.latitude, props.location.longitude], 15, { animate: false })
  } else if (points.length) {
    map.fitBounds(L.latLngBounds(points).pad(0.18), { maxZoom: 15, animate: false })
  }
}
watch(() => [props.branches, props.location], render)
watch(() => props.selectedId, (id) => {
  const marker = id ? markers.get(id) : null
  if (marker && map) {
    map.setView(marker.getLatLng(), 15)
    marker.openPopup()
  }
})
onMounted(async () => {
  await nextTick()
  if (!container.value) return
  map = L.map(container.value, { scrollWheelZoom: false, zoomControl: false }).setView([41.3111, 69.2797], 11)
  L.control.zoom({
    position: "bottomright",
    zoomInTitle: "Yaqinlashtirish",
    zoomOutTitle: "Uzoqlashtirish",
  }).addTo(map)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
    referrerPolicy: "strict-origin-when-cross-origin",
  }).on("tileerror", () => { tileError.value = true }).addTo(map)
  layer = L.layerGroup().addTo(map)
  observer = new ResizeObserver(() => map?.invalidateSize())
  observer.observe(container.value)
  render()
})
onBeforeUnmount(() => { observer?.disconnect(); map?.remove(); map = null })
</script>

<template>
  <div class="nearby-map-shell">
    <div ref="container" class="nearby-map" role="region" aria-label="Yaqin xizmatlar xaritasi" />
    <p v-if="tileError" class="map-notice" role="status">Xarita rasmlari yuklanmadi. Internet aloqasini tekshirib, sahifani yangilang.</p>
  </div>
</template>

<style scoped>
.nearby-map-shell { position: relative; height: 100%; min-height: 360px; }
.nearby-map { width: 100%; height: 100%; min-height: 360px; z-index: 0; }
.map-notice { position: absolute; z-index: 1; left: 12px; right: 12px; bottom: 22px; padding: 12px; border-radius: 12px; color: var(--text); background: var(--panel); font-size: 13px; }
.nearby-map :deep(.leaflet-control-zoom a) { width: 44px; height: 44px; line-height: 44px; }
.nearby-map :deep(.service-map-marker), .nearby-map :deep(.user-map-marker) { background: transparent; border: 0; }
.nearby-map :deep(.service-map-badge) { position: relative; display: grid; place-items: center; width: 40px; height: 40px; border: 3px solid white; border-radius: 14px; background: var(--marker-color); color: white; box-shadow: 0 3px 12px #0f172a40; }
.nearby-map :deep(.service-map-badge::after) { content: ""; position: absolute; bottom: -9px; left: 50%; width: 12px; height: 12px; border-right: 3px solid white; border-bottom: 3px solid white; border-radius: 0 0 3px 0; background: var(--marker-color); transform: translateX(-50%) rotate(45deg); }
.nearby-map :deep(.service-map-badge svg) { position: relative; z-index: 1; width: 20px; height: 20px; }
.nearby-map :deep(.user-map-badge) { display: grid; place-items: center; width: 44px; height: 44px; margin: 2px; border: 3px solid white; border-radius: 13px; background: #0284c7; color: white; transform: rotate(45deg); box-shadow: 0 0 0 7px #0ea5e92b, 0 3px 14px #07598555; }
.nearby-map :deep(.user-map-badge svg) { width: 25px; height: 25px; transform: rotate(-45deg); }
.nearby-map :deep(.user-map-label) { border: 1px solid #bae6fd; border-radius: 8px; background: #f0f9ff; color: #075985; font-size: 12px; font-weight: 750; box-shadow: 0 2px 8px #07598520; }
.nearby-map :deep(.leaflet-marker-icon:focus-visible) { outline: 3px solid #0f172a; outline-offset: 5px; border-radius: 14px; }
</style>
