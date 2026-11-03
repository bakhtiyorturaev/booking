<script setup lang="ts">
import { icon, type IconDefinition } from "@fortawesome/fontawesome-svg-core"
import { faGamepad, faDesktop, faScissors, faDumbbell, faFutbol, faBuilding, faStore, faPerson, faCircleDot } from "@fortawesome/free-solid-svg-icons"
import type { BranchListSummary } from "~/types/club"

// Google Maps variant of NearbyMap. Emits "failed" so the page can fall back to the Leaflet map.
const props = defineProps<{
  branches: BranchListSummary[]
  location: { latitude: number; longitude: number } | null
  selectedId: string | null
}>()
const emit = defineEmits<{ select: [id: string]; failed: [] }>()
const config = useRuntimeConfig()
const container = ref<HTMLDivElement | null>(null)
let map: any = null
let infoWindow: any = null
let MarkerClass: any = null
let userMarker: any = null
const markers = new Map<string, any>()

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

let loader: Promise<any> | null = null
const loadGoogleMaps = (key: string) => {
  const w = window as any
  if (w.google?.maps?.importLibrary) return Promise.resolve(w.google)
  if (loader) return loader
  loader = new Promise((resolve, reject) => {
    w.gm_authFailure = () => emit("failed")
    w.__onGoogleMapsReady = () => resolve(w.google)
    const script = document.createElement("script")
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly&loading=async&language=uz&region=UZ&callback=__onGoogleMapsReady`
    script.async = true
    script.onerror = () => { loader = null; reject(new Error("Google Maps script failed")) }
    document.head.appendChild(script)
  })
  return loader
}

const render = () => {
  if (!map || !MarkerClass) return
  markers.forEach(marker => { marker.map = null })
  markers.clear()
  if (userMarker) { userMarker.map = null; userMarker = null }
  const g = (window as any).google
  const bounds = new g.maps.LatLngBounds()
  let points = 0
  for (const branch of props.branches) {
    if (branch.latitude == null || branch.longitude == null || branch.latitude === "" || branch.longitude === "") continue
    const lat = Number(branch.latitude)
    const lng = Number(branch.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) continue
    const { symbol, color } = serviceSymbol(branch)
    const badge = document.createElement("span")
    badge.className = "service-map-badge"
    badge.style.setProperty("--marker-color", color)
    badge.innerHTML = icon(symbol).html.join("")
    const marker = new MarkerClass({ map, position: { lat, lng }, content: badge, title: `${branch.club.name} — ${branch.name}`, gmpClickable: true })
    marker.addListener("gmp-click", () => { emit("select", branch.id); openPopup(branch, marker) })
    markers.set(branch.id, marker)
    bounds.extend({ lat, lng })
    points++
  }
  if (props.location) {
    const wrap = document.createElement("div")
    wrap.className = "user-map-wrap"
    const userBadge = document.createElement("span")
    userBadge.className = "user-map-badge"
    userBadge.innerHTML = icon(faPerson).html.join("")
    const label = document.createElement("span")
    label.className = "user-map-label"
    label.textContent = "Siz shu yerdasiz"
    wrap.append(userBadge, label)
    userMarker = new MarkerClass({ map, position: { lat: props.location.latitude, lng: props.location.longitude }, content: wrap, title: "Sizning joylashuvingiz", zIndex: 1000 })
    map.setCenter({ lat: props.location.latitude, lng: props.location.longitude })
    map.setZoom(15)
  } else if (points) {
    map.fitBounds(bounds, 60)
    if (points === 1) map.setZoom(15)
  }
}

const openPopup = (branch: BranchListSummary, marker: any) => {
  const popup = document.createElement("div")
  popup.className = "google-map-popup"
  const title = document.createElement("strong")
  title.textContent = `${branch.club.name} — ${branch.name}`
  const address = document.createElement("p")
  address.textContent = branch.full_address || branch.address
  const link = document.createElement("a")
  link.href = `/branches/${encodeURIComponent(branch.id)}`
  link.textContent = "Ko‘rish va bron qilish →"
  popup.append(title, address, link)
  infoWindow.setContent(popup)
  infoWindow.open({ map, anchor: marker })
}

watch(() => [props.branches, props.location], render)
watch(() => props.selectedId, (id) => {
  const marker = id ? markers.get(id) : null
  const branch = id ? props.branches.find(item => item.id === id) : null
  if (marker && branch && map) {
    map.setCenter(marker.position)
    map.setZoom(15)
    openPopup(branch, marker)
  }
})

onMounted(async () => {
  await nextTick()
  const key = String(config.public.googleMapsKey || "")
  if (!container.value || !key) { emit("failed"); return }
  try {
    const g = await loadGoogleMaps(key)
    const { Map, InfoWindow } = await g.maps.importLibrary("maps")
    const { AdvancedMarkerElement } = await g.maps.importLibrary("marker")
    if (!container.value) return
    MarkerClass = AdvancedMarkerElement
    map = new Map(container.value, {
      center: { lat: 41.3111, lng: 69.2797 },
      zoom: 11,
      mapId: String(config.public.googleMapsMapId || "DEMO_MAP_ID"),
      gestureHandling: "cooperative",
      streetViewControl: false,
      mapTypeControl: false,
      fullscreenControl: false,
      zoomControlOptions: { position: g.maps.ControlPosition.RIGHT_BOTTOM },
    })
    infoWindow = new InfoWindow()
    render()
  } catch {
    emit("failed")
  }
})
onBeforeUnmount(() => { markers.forEach(marker => { marker.map = null }); markers.clear(); map = null })
</script>

<template>
  <div class="nearby-map-shell">
    <div ref="container" class="nearby-map" role="region" aria-label="Yaqin xizmatlar xaritasi" />
  </div>
</template>

<style scoped>
.nearby-map-shell { position: relative; height: 100%; min-height: 360px; }
.nearby-map { width: 100%; height: 100%; min-height: 360px; z-index: 0; }
.nearby-map :deep(.service-map-badge) { position: relative; display: grid; place-items: center; width: 40px; height: 40px; margin-bottom: 9px; border: 3px solid white; border-radius: 14px; background: var(--marker-color); color: white; box-shadow: 0 3px 12px #0f172a40; }
.nearby-map :deep(.service-map-badge::after) { content: ""; position: absolute; bottom: -9px; left: 50%; width: 12px; height: 12px; border-right: 3px solid white; border-bottom: 3px solid white; border-radius: 0 0 3px 0; background: var(--marker-color); transform: translateX(-50%) rotate(45deg); }
.nearby-map :deep(.service-map-badge svg) { position: relative; z-index: 1; width: 20px; height: 20px; }
.nearby-map :deep(.user-map-wrap) { display: grid; justify-items: center; gap: 10px; transform: translateY(50%); }
.nearby-map :deep(.user-map-badge) { display: grid; place-items: center; width: 44px; height: 44px; border: 3px solid white; border-radius: 13px; background: #0284c7; color: white; transform: rotate(45deg); box-shadow: 0 0 0 7px #0ea5e92b, 0 3px 14px #07598555; }
.nearby-map :deep(.user-map-badge svg) { width: 25px; height: 25px; transform: rotate(-45deg); }
.nearby-map :deep(.user-map-label) { padding: 4px 8px; border: 1px solid #bae6fd; border-radius: 8px; background: #f0f9ff; color: #075985; font-size: 12px; font-weight: 750; white-space: nowrap; box-shadow: 0 2px 8px #07598520; }
.nearby-map :deep(.google-map-popup) { max-width: 240px; color: #0f172a; font-size: 13px; }
.nearby-map :deep(.google-map-popup p) { margin: 6px 0; color: #475569; }
</style>
