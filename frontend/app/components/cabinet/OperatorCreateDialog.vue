<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import type { Map as LeafletMap, LayerGroup as LeafletLayerGroup, Marker as LeafletMarker } from "leaflet"
import { useAdminApi } from "~/api/admin"
const props = defineProps<{ clubId?: string; branchId?: string }>()
const emit = defineEmits<{ saved: [] }>()
const { isStaff } = useCabinetAccess()
const api = useAdminApi()
const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref("")
const customers = ref<any[]>([])
const resources = ref<any[]>([])
const cities = ref<any[]>([])
const form = ref({ user: "", resource: "", full_name: "", phone: "", billing_city: "", billing_district: "", work_start_time: "09:00", work_end_time: "20:00" })
const { districts, isDistrictLoading, districtError } = useCityDistricts(() => form.value.billing_city)
const title = "Sartarosh qo‘shish"
const dialogId = "operator-barber-dialog"

// Xarita orqali filial tanlash
const DEFAULT_LAT = 41.2995
const DEFAULT_LNG = 69.2401
const mapEl = ref<HTMLElement | null>(null)
let L: typeof import("leaflet") | null = null
let mapInstance: LeafletMap | null = null
let markersLayer: LeafletLayerGroup | null = null
const markerById = new Map<string, LeafletMarker>()
const resourcePoints = computed(() => resources.value
  .map(resource => {
    const lat = Number(resource.latitude)
    const lng = Number(resource.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null
    return { resource, lat, lng }
  })
  .filter((item): item is { resource: any; lat: number; lng: number } => item !== null))
const resourceLabel = (resource: any) => {
  const prefix = resource.branch_name || resource.club_name || ""
  return prefix ? `${prefix} — ${resource.name}` : resource.name
}
const markerIcon = (selected: boolean) => {
  const el = document.createElement("span")
  el.className = `resource-map-pin${selected ? " selected" : ""}`
  return L!.divIcon({ html: el, className: "resource-map-marker", iconSize: [26, 26], iconAnchor: [13, 13] })
}
const renderMarkers = () => {
  if (!L || !markersLayer) return
  markersLayer.clearLayers()
  markerById.clear()
  const points: [number, number][] = []
  for (const { resource, lat, lng } of resourcePoints.value) {
    points.push([lat, lng])
    const marker = L.marker([lat, lng], { icon: markerIcon(form.value.resource === resource.id) })
      .bindTooltip(resourceLabel(resource), { direction: "top" })
      .on("click", () => { form.value.resource = resource.id })
    marker.addTo(markersLayer)
    markerById.set(resource.id, marker)
  }
  if (points.length) mapInstance?.fitBounds(L.latLngBounds(points).pad(0.25), { maxZoom: 15 })
}
const initResourceMap = async () => {
  if (!mapEl.value || mapInstance || !resourcePoints.value.length) return
  const leaflet = await import("leaflet")
  L = ((leaflet as any).default ?? leaflet) as typeof import("leaflet")
  mapInstance = L.map(mapEl.value, { scrollWheelZoom: false }).setView([DEFAULT_LAT, DEFAULT_LNG], 11)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 19,
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(mapInstance)
  markersLayer = L.layerGroup().addTo(mapInstance)
  renderMarkers()
}
const destroyMap = () => {
  mapInstance?.remove()
  mapInstance = null
  markersLayer = null
  markerById.clear()
}
watch(() => form.value.resource, () => {
  for (const [id, marker] of markerById) marker.setIcon(markerIcon(form.value.resource === id))
})
onBeforeUnmount(destroyMap)

const close = () => { if (!saving.value) { open.value = false; destroyMap() } }
useDialogFocus(open, `#${dialogId}`, close)
const allPages = async (fetcher: (params: Record<string, any>) => Promise<any>, params: Record<string, any>) => {
  const items: any[] = []; let page = 1; let next = true
  while (next) { const response = await fetcher({ ...params, page: page++, page_size: 100 }); items.push(...response.results); next = Boolean(response.next) }
  return items
}
const begin = async () => {
  open.value = true; loading.value = true; error.value = ""
  form.value = { user: "", resource: "", full_name: "", phone: "", billing_city: "", billing_district: "", work_start_time: "09:00", work_end_time: "20:00" }
  destroyMap()
  try {
    const results = await Promise.all([
      allPages(api.getUsers, { status: "ACTIVE" }),
      allPages(api.getBranches, props.clubId ? { club_id: props.clubId } : {}),
    ])
    customers.value = results[0].filter(account => ["CUSTOMER", "CLIENT"].includes(account.role))
    resources.value = results[1]
    cities.value = await api.getCities()
    const clubs = await allPages(api.getClubs, { category: "BARBERSHOP" })
    const ids = new Set(clubs.map(club => club.id))
    resources.value = resources.value.filter(branch => ids.has(typeof branch.club === "string" ? branch.club : branch.club?.id))
    if (props.branchId && resources.value.some(branch => branch.id === props.branchId)) form.value.resource = props.branchId
    else if (props.clubId && resources.value.length) form.value.resource = resources.value[0].id
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally {
    loading.value = false
    await nextTick()
    await initResourceMap()
  }
}
const save = async () => {
  if (saving.value) return
  saving.value = true; error.value = ""
  try {
    const branch = resources.value.find(item => item.id === form.value.resource)
    if (props.clubId && !branch) throw new Error("Avval ushbu sartaroshxona uchun filial yarating va uni tanlang.")
    await api.createBarber({ user: form.value.user, branch: branch?.id || null, club: branch ? (typeof branch.club === "string" ? branch.club : branch.club.id) : null, billing_city: branch ? null : form.value.billing_city || null, billing_district: branch ? null : form.value.billing_district || null, full_name: form.value.full_name, phone: form.value.phone, affiliation_status: "APPROVED", status: "AVAILABLE", work_start_time: form.value.work_start_time, work_end_time: form.value.work_end_time, working_days: [1, 2, 3, 4, 5, 6, 7] })
    open.value = false; emit("saved"); useToast().success("Saqlandi.")
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally { saving.value = false }
}
</script>
<template>
  <button v-if="isStaff" type="button" class="primary-button" @click="begin"><CabinetIcon name="plus" />{{ title }}</button>
  <Teleport to="body">
    <div v-if="open" :id="dialogId" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" :aria-labelledby="`${dialogId}-title`" tabindex="-1" @click.self="close">
      <div class="modal-card"><div class="modal-header"><h2 :id="`${dialogId}-title`">{{ title }}</h2><button type="button" class="modal-close-btn" aria-label="Yopish" :disabled="saving" @click="close"><CabinetIcon name="close" /></button></div>
        <form class="modal-form" @submit.prevent="save">
          <p v-if="error" class="form-error" role="alert">{{ error }}</p><p v-if="loading">Yuklanmoqda…</p>
          <template v-else>
            <div class="form-group"><label :for="`${dialogId}-user`">Akkaunt</label><select :id="`${dialogId}-user`" v-model="form.user" required :disabled="saving"><option value="" disabled>Tanlang</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.profile?.full_name || customer.username }} — {{ customer.phone }}</option></select></div>
            <p class="account-hint">Botda bronni qabul qilish uchun sartarosh avval o‘z Telegram akkauntidan saytga kirib, botda /start bosishi kerak. Shu akkauntni tanlang.</p>
            <div class="form-group"><label :for="`${dialogId}-resource`">Filial</label><select :id="`${dialogId}-resource`" v-model="form.resource" :disabled="saving"><option v-if="!clubId" value="">Mustaqil sartarosh</option><option v-else value="" disabled>Filialni tanlang</option><option v-for="resource in resources" :key="resource.id" :value="resource.id">{{ resource.branch_name || resource.club_name }} — {{ resource.name }}</option></select></div>
            <div v-if="resourcePoints.length" class="form-group">
              <label>Xaritadan tanlash</label>
              <div ref="mapEl" class="resource-map" />
              <small class="map-hint">Filialni xaritadagi belgidan bosib ham tanlashingiz mumkin.</small>
            </div>
            <div v-if="!form.resource && !clubId" class="form-group"><label :for="`${dialogId}-city`">Shahar</label><select :id="`${dialogId}-city`" v-model="form.billing_city" required :disabled="saving" @change="form.billing_district = ''"><option value="" disabled>Tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option></select></div><div v-if="!form.resource && !clubId" class="form-group"><label :for="`${dialogId}-district`">Tuman</label><select :id="`${dialogId}-district`" v-model="form.billing_district" required :disabled="saving || isDistrictLoading || !form.billing_city"><option value="" disabled>{{ isDistrictLoading ? 'Yuklanmoqda…' : 'Tumanni tanlang' }}</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option></select><small v-if="districtError" role="alert">{{ districtError }}</small><small v-else-if="form.billing_city && !isDistrictLoading && !districts.length">Bu hudud uchun tumanlar hali qo‘shilmagan.</small></div><div class="form-group"><label :for="`${dialogId}-name`">Ism-familiya</label><input :id="`${dialogId}-name`" v-model="form.full_name" maxlength="180" required :disabled="saving"></div><div class="form-group"><label :for="`${dialogId}-phone`">Telefon</label><input :id="`${dialogId}-phone`" v-model="form.phone" type="tel" :disabled="saving"></div>
            <div class="form-group"><label :for="`${dialogId}-start`">Ish boshlanishi</label><input :id="`${dialogId}-start`" v-model="form.work_start_time" type="time" required :disabled="saving"></div>
            <div class="form-group"><label :for="`${dialogId}-end`">Ish tugashi</label><input :id="`${dialogId}-end`" v-model="form.work_end_time" type="time" required :disabled="saving"></div>
            <p v-if="clubId && !resources.length" class="form-error">Avval sartaroshxonaga filial qo‘shing.</p>
          </template>
          <div class="modal-actions"><button type="button" class="secondary-button" :disabled="saving" @click="close">Bekor qilish</button><button type="submit" class="primary-button" :disabled="saving || loading || (Boolean(clubId) && !form.resource) || (!form.resource && isDistrictLoading)">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button></div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
<style scoped>
.resource-map { height: 220px; border-radius: 10px; border: 1px solid var(--border); overflow: hidden; z-index: 0; }
.map-hint { font-size: 11px; color: var(--muted); }
:global(.resource-map-marker) { background: transparent; border: 0; }
:global(.resource-map-pin) { display: block; width: 20px; height: 20px; margin: 3px; border: 3px solid white; border-radius: 50%; background: #6366f1; box-shadow: 0 2px 8px #0f172a40; cursor: pointer; }
:global(.resource-map-pin.selected) { background: #16a34a; box-shadow: 0 0 0 4px #16a34a33, 0 2px 8px #0f172a40; }
</style>
