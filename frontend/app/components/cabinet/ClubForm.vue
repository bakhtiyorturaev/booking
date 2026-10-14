<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet"
import { useAdminApi } from "~/api/admin"
import type { ServiceTypeManagementItem } from "~/api/serviceTypes"
import { serviceTreeOptions } from "~/utils/serviceTree"
import ServiceChecklist from "~/components/cabinet/ServiceChecklist.vue"

const props = defineProps<{ clubId?: string }>()

const DEFAULT_LAT = 41.2995
const DEFAULT_LNG = 69.2401
const MAX_IMAGE_SIZE = 5 * 1024 * 1024
const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]

const route = useRoute()
const cabinetPath = useCabinetPath()
const adminApi = useAdminApi()
const { isStaff: isPlatformAdmin } = useCabinetAccess()

const isEdit = computed(() => Boolean(props.clubId))
const listPath = computed(() => cabinetPath("/clubs"))

useHead({ title: computed(() => (isEdit.value ? "Xizmatni tahrirlash" : "Yangi xizmat qo‘shish")) })

const services = ref<ServiceTypeManagementItem[]>([])
const serviceChoices = computed(() => serviceTreeOptions(services.value.filter(service => service.is_active)))
const cities = ref<any[]>([])
const clientsList = ref<any[]>([])

const form = ref({
  name: "",
  owner: null as string | null,
  available_services: [] as string[],
  service_type: "",
  billing_city: "",
  billing_district: "",
  description: "",
  phone: "",
  email: "",
  website: "",
  address: "",
  latitude: null as number | null,
  longitude: null as number | null,
  status: "ACTIVE",
  is_verified: false,
})

watch(() => form.value.service_type, id => {
  if (id && !form.value.available_services.includes(id)) form.value.available_services.push(id)
})

const { districts, isDistrictLoading, districtError } = useCityDistricts(() => form.value.billing_city)

const isLoading = ref(true)
const isSaving = ref(false)
const errorMessage = ref("")

// Rasmlar
const logoFile = ref<File | null>(null)
const coverFile = ref<File | null>(null)
const logoPreview = ref("")
const coverPreview = ref("")
const objectUrls: string[] = []

const pickImage = (event: Event, kind: "logo" | "cover") => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!IMAGE_TYPES.includes(file.type)) {
    errorMessage.value = "Rasm JPG, PNG yoki WEBP formatida bo‘lishi kerak."
    input.value = ""
    return
  }
  if (file.size > MAX_IMAGE_SIZE) {
    errorMessage.value = "Rasm hajmi 5 MB dan oshmasligi kerak."
    input.value = ""
    return
  }
  errorMessage.value = ""
  const url = URL.createObjectURL(file)
  objectUrls.push(url)
  if (kind === "logo") { logoFile.value = file; logoPreview.value = url } else { coverFile.value = file; coverPreview.value = url }
}

// Xarita
const mapEl = ref<HTMLElement | null>(null)
let L: typeof import("leaflet") | null = null
let mapInstance: LeafletMap | null = null
let markerInstance: LeafletMarker | null = null

const setLocation = (lat: number, lng: number) => {
  form.value.latitude = Number(lat.toFixed(6))
  form.value.longitude = Number(lng.toFixed(6))
  if (!L || !mapInstance) return
  if (markerInstance) {
    markerInstance.setLatLng([lat, lng])
    return
  }
  const marker = L.marker([lat, lng], { draggable: true }).addTo(mapInstance)
  marker.on("dragend", () => {
    const position = marker.getLatLng()
    setLocation(position.lat, position.lng)
  })
  markerInstance = marker
}

const clearLocation = () => {
  form.value.latitude = null
  form.value.longitude = null
  markerInstance?.remove()
  markerInstance = null
}

const useMyLocation = () => {
  if (!navigator.geolocation) return
  navigator.geolocation.getCurrentPosition(
    position => {
      setLocation(position.coords.latitude, position.coords.longitude)
      mapInstance?.setView([position.coords.latitude, position.coords.longitude], 16)
    },
    () => { errorMessage.value = "Joylashuvni aniqlab bo‘lmadi. Xaritadan qo‘lda tanlang." },
    { enableHighAccuracy: true, timeout: 10000 },
  )
}

const initMap = async () => {
  if (!mapEl.value || mapInstance) return
  const leaflet = await import("leaflet")
  L = ((leaflet as any).default ?? leaflet) as typeof import("leaflet")
  const [{ default: iconUrl }, { default: iconRetinaUrl }, { default: shadowUrl }] = await Promise.all([
    import("leaflet/dist/images/marker-icon.png"),
    import("leaflet/dist/images/marker-icon-2x.png"),
    import("leaflet/dist/images/marker-shadow.png"),
  ])
  delete (L.Icon.Default.prototype as any)._getIconUrl
  L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl })

  const hasPoint = form.value.latitude != null && form.value.longitude != null
  mapInstance = L.map(mapEl.value).setView([form.value.latitude ?? DEFAULT_LAT, form.value.longitude ?? DEFAULT_LNG], hasPoint ? 16 : 12)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 19,
    // Sayt `Referrer-Policy: same-origin` yuboradi, OSM esa tile so'rovlarida Referer talab qiladi.
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(mapInstance)
  mapInstance.on("click", (event: any) => setLocation(event.latlng.lat, event.latlng.lng))
  if (hasPoint) setLocation(form.value.latitude!, form.value.longitude!)
}

const loadClients = async () => {
  if (!isPlatformAdmin.value) return
  try {
    let page = 1
    const clients: any[] = []
    let next = true
    while (next) {
      const res = await adminApi.getUsers({ role: "CLIENT", status: "ACTIVE", page_size: 100, page: page++ })
      clients.push(...res.results)
      next = Boolean(res.next)
    }
    clientsList.value = clients
  } catch (error) {
    console.error("Failed to fetch clients", error)
  }
}

const loadClub = async () => {
  if (!props.clubId) return
  const club = await adminApi.getClub(props.clubId)
  form.value = {
    name: club.name || "",
    owner: club.owner || club.owner_details?.id || null,
    available_services: [...(club.available_services || [])],
    service_type: club.service_type || "",
    billing_city: club.billing_city || "",
    billing_district: club.billing_district || "",
    description: club.description || "",
    phone: club.phone || "",
    email: club.email || "",
    website: club.website || "",
    address: club.address || "",
    latitude: club.latitude != null ? Number(club.latitude) : null,
    longitude: club.longitude != null ? Number(club.longitude) : null,
    status: club.status || "ACTIVE",
    is_verified: Boolean(club.is_verified),
  }
  logoPreview.value = club.logo || ""
  coverPreview.value = club.cover || ""
}

// Yangi mijoz (egasi) qo'shish
const showNewClient = ref(false)
const creatingClient = ref(false)
const newClient = ref({ full_name: "", phone: "", username: "", password: "" })
const createClientHere = async () => {
  if (creatingClient.value) return
  creatingClient.value = true
  errorMessage.value = ""
  try {
    const client = await adminApi.createUser({ ...newClient.value })
    clientsList.value.push(client)
    form.value.owner = client.id
    showNewClient.value = false
    newClient.value = { full_name: "", phone: "", username: "", password: "" }
  } catch (error) {
    errorMessage.value = cabinetErrorMessage(error)
  } finally {
    creatingClient.value = false
  }
}

const buildPayload = () => {
  const data = new FormData()
  const f = form.value
  data.append("name", f.name.trim())
  if (f.service_type) data.append("service_type", f.service_type)
  f.available_services.forEach(id => data.append("available_services", id))
  if (f.billing_city) data.append("billing_city", f.billing_city)
  if (f.billing_district) data.append("billing_district", f.billing_district)
  if (isPlatformAdmin.value && f.owner) data.append("owner", f.owner)
  data.append("description", f.description)
  data.append("phone", f.phone)
  data.append("email", f.email)
  data.append("website", f.website)
  data.append("address", f.address)
  if (f.latitude != null && f.longitude != null) {
    data.append("latitude", f.latitude.toFixed(6))
    data.append("longitude", f.longitude.toFixed(6))
  }
  data.append("status", f.status)
  data.append("is_verified", f.is_verified ? "true" : "false")
  if (logoFile.value) data.append("logo", logoFile.value)
  if (coverFile.value) data.append("cover", coverFile.value)
  return data
}

const save = async () => {
  if (isSaving.value) return
  if (!form.value.name.trim()) {
    errorMessage.value = "Xizmat nomini kiriting"
    return
  }
  isSaving.value = true
  errorMessage.value = ""
  try {
    const payload = buildPayload()
    if (props.clubId) await adminApi.updateClub(props.clubId, payload)
    else await adminApi.createClub(payload)
    await navigateTo(listPath.value)
  } catch (error) {
    errorMessage.value = cabinetErrorMessage(error)
  } finally {
    isSaving.value = false
  }
}

onMounted(async () => {
  try {
    const [serviceList, cityList] = await Promise.all([adminApi.getServiceTypes(), adminApi.getCities()])
    services.value = serviceList
    cities.value = cityList
    await Promise.all([loadClients(), loadClub()])
    if (!isEdit.value) {
      form.value.is_verified = Boolean(isPlatformAdmin.value)
      if (isPlatformAdmin.value && typeof route.query.owner === "string") form.value.owner = route.query.owner
    }
  } catch (error) {
    errorMessage.value = cabinetErrorMessage(error)
  } finally {
    isLoading.value = false
  }
  await nextTick()
  await initMap()
})

onBeforeUnmount(() => {
  mapInstance?.remove()
  mapInstance = null
  markerInstance = null
  objectUrls.forEach(url => URL.revokeObjectURL(url))
})
</script>

<template>
  <div class="club-form-page">
    <div class="club-form-header">
      <NuxtLink :to="listPath" class="secondary-button">← Xizmatlarga qaytish</NuxtLink>
      <h1>{{ isEdit ? "Xizmatni tahrirlash" : "Yangi xizmat qo‘shish" }}</h1>
    </div>

    <div v-if="isLoading" class="club-form-loading">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <form v-show="!isLoading" class="club-form-card" @submit.prevent="save">
      <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

      <section class="club-form-section">
        <h2>Asosiy ma’lumotlar</h2>
        <div class="form-row">
          <div class="form-group">
            <label for="club-name">Nomi *</label>
            <input id="club-name" v-model="form.name" type="text" placeholder="Xizmat nomi" required>
          </div>
          <div class="form-group">
            <label for="club-service-type">Xizmat turi *</label>
            <select id="club-service-type" v-model="form.service_type" :disabled="!isPlatformAdmin && isEdit" required>
              <option value="" disabled>Xizmatni tanlang</option>
              <option v-for="service in serviceChoices" :key="service.id" :value="service.id">{{ service.label }}</option>
            </select>
          </div>
        </div>
        <fieldset class="service-picker">
          <legend>Klub xizmatlari</legend>
          <ServiceChecklist v-model="form.available_services" :services="serviceChoices" />
        </fieldset>
        <div class="form-group">
          <label for="club-description">Tavsif</label>
          <textarea id="club-description" v-model="form.description" rows="3" placeholder="Xizmat haqida" />
        </div>
      </section>

      <section class="club-form-section">
        <h2>Rasmlar</h2>
        <div class="form-row">
          <div class="form-group">
            <label for="club-logo">Logotip</label>
            <input id="club-logo" type="file" accept="image/jpeg,image/png,image/webp" @change="pickImage($event, 'logo')">
            <img v-if="logoPreview" :src="logoPreview" alt="Logotip" class="club-logo-preview">
          </div>
          <div class="form-group">
            <label for="club-cover">Muqova rasmi</label>
            <input id="club-cover" type="file" accept="image/jpeg,image/png,image/webp" @change="pickImage($event, 'cover')">
            <img v-if="coverPreview" :src="coverPreview" alt="Muqova" class="club-cover-preview">
          </div>
        </div>
        <small class="club-form-hint">JPG, PNG yoki WEBP, 5 MB gacha.</small>
      </section>

      <section class="club-form-section">
        <h2>Joylashuv</h2>
        <div class="form-row">
          <div class="form-group">
            <label for="billing-city">Shahar *</label>
            <select id="billing-city" v-model="form.billing_city" required :disabled="!isPlatformAdmin && isEdit" @change="form.billing_district = ''">
              <option value="" disabled>Shaharni tanlang</option>
              <option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="billing-district">Tuman *</label>
            <select id="billing-district" v-model="form.billing_district" required :disabled="isDistrictLoading || !form.billing_city || (!isPlatformAdmin && isEdit)">
              <option value="" disabled>{{ isDistrictLoading ? "Yuklanmoqda…" : "Tumanni tanlang" }}</option>
              <option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option>
            </select>
            <small v-if="districtError" role="alert">{{ districtError }}</small>
            <small v-else-if="form.billing_city && !isDistrictLoading && !districts.length">Bu hudud uchun tumanlar hali qo‘shilmagan.</small>
          </div>
        </div>
        <div class="form-group">
          <label for="club-address">Manzil</label>
          <input id="club-address" v-model="form.address" type="text" placeholder="Ko‘cha, uy, mo‘ljal...">
        </div>
        <div class="form-group">
          <label>Xaritadan joyni tanlang</label>
          <div ref="mapEl" class="club-location-map" />
          <div class="club-map-actions">
            <small class="club-form-hint">
              <template v-if="form.latitude != null && form.longitude != null">Tanlangan: {{ form.latitude.toFixed(6) }}, {{ form.longitude.toFixed(6) }}</template>
              <template v-else>Xaritada bosing yoki belgini sudrab joyni ko‘rsating.</template>
            </small>
            <div class="club-map-buttons">
              <button type="button" class="secondary-button" @click="useMyLocation">Mening joylashuvim</button>
              <button v-if="form.latitude != null" type="button" class="secondary-button" @click="clearLocation">Tozalash</button>
            </div>
          </div>
        </div>
      </section>

      <section class="club-form-section">
        <h2>Aloqa</h2>
        <div class="form-row">
          <div class="form-group">
            <label for="club-phone">Telefon</label>
            <input id="club-phone" v-model="form.phone" type="tel" placeholder="+998 90 123 45 67">
          </div>
          <div class="form-group">
            <label for="club-email">Email</label>
            <input id="club-email" v-model="form.email" type="email" placeholder="info@club.uz">
          </div>
        </div>
        <div class="form-group">
          <label for="club-website">Vebsayt</label>
          <input id="club-website" v-model="form.website" type="url" placeholder="https://club.uz">
        </div>
      </section>

      <section class="club-form-section">
        <h2>Boshqaruv</h2>
        <div v-if="isPlatformAdmin" class="form-group">
          <label for="club-owner">Xizmat egasi</label>
          <button type="button" class="secondary-button" @click="showNewClient = !showNewClient">Mijoz qo‘shish</button>
          <div v-if="showNewClient" class="inline-client-form">
            <label for="new-owner-name">Ism-familiya</label><input id="new-owner-name" v-model="newClient.full_name" maxlength="150" autocomplete="name">
            <label for="new-owner-phone">Telefon</label><input id="new-owner-phone" v-model="newClient.phone" type="tel" autocomplete="tel">
            <label for="new-owner-login">Login</label><input id="new-owner-login" v-model="newClient.username" maxlength="30" autocomplete="off" autocapitalize="none">
            <label for="new-owner-password">Parol</label><input id="new-owner-password" v-model="newClient.password" type="password" maxlength="128" autocomplete="new-password">
            <button type="button" class="primary-button" :disabled="creatingClient" @click="createClientHere">{{ creatingClient ? "Saqlanmoqda…" : "Mijozni saqlash" }}</button>
          </div>
          <select id="club-owner" v-model="form.owner">
            <option :value="null">O‘zim (Platforma administratori)</option>
            <option v-for="cl in clientsList" :key="cl.id" :value="cl.id">{{ cl.profile?.full_name || cl.username }} (@{{ cl.username }})</option>
          </select>
        </div>
        <div class="form-group">
          <label for="club-status">Holat</label>
          <select id="club-status" v-model="form.status">
            <option value="ACTIVE">Faol</option>
            <option value="INACTIVE">Nofaol</option>
          </select>
        </div>
        <div v-if="isPlatformAdmin" class="form-checkbox">
          <label><input v-model="form.is_verified" type="checkbox"><span>Tekshiruvdan o‘tgan deb belgilash (Verified badge)</span></label>
        </div>
      </section>

      <div class="club-form-actions">
        <NuxtLink :to="listPath" class="secondary-button">Bekor qilish</NuxtLink>
        <button type="submit" class="primary-button" :disabled="isSaving || creatingClient || isDistrictLoading">
          {{ isSaving ? "Saqlanmoqda..." : "Saqlash" }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.club-form-page { display: flex; flex-direction: column; gap: 16px; max-width: 880px; width: 100%; margin: 0 auto; }
.club-form-header { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.club-form-header h1 { margin: 0; font-size: 22px; font-weight: 800; }
.club-form-loading { display: flex; flex-direction: column; align-items: center; padding: 60px; gap: 12px; color: var(--muted); }
.club-form-card { display: flex; flex-direction: column; gap: 22px; padding: 24px; background: var(--surface); border: 1px solid var(--panel-border); border-radius: 20px; }
.club-form-section { display: flex; flex-direction: column; gap: 14px; }
.club-form-section h2 { margin: 0; font-size: 15px; font-weight: 750; padding-bottom: 8px; border-bottom: 1px solid var(--panel-border); }
.form-row { display: flex; gap: 12px; flex-wrap: wrap; }
.form-row > .form-group { min-width: 220px; }
.form-group { display: flex; flex-direction: column; gap: 6px; flex: 1; }
.form-group label { font-size: 12px; font-weight: 600; color: var(--muted); }
.form-group input, .form-group textarea, .form-group select { padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--control); color: var(--text); font-size: 13px; }
.form-checkbox label { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; }
.form-error { margin: 0; padding: 10px; border-radius: 8px; background: rgba(239, 68, 68, 0.15); color: #ef4444; font-size: 12px; }
.inline-client-form { display: grid; gap: 8px; padding: 16px; border: 1px solid var(--panel-border); border-radius: 10px; margin: 10px 0; }
.club-logo-preview { width: 96px; height: 96px; object-fit: cover; border-radius: 10px; border: 1px solid var(--border); margin-top: 6px; }
.club-cover-preview { width: 100%; max-width: 280px; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 10px; border: 1px solid var(--border); margin-top: 6px; }
.club-location-map { height: 340px; border-radius: 12px; border: 1px solid var(--border); overflow: hidden; z-index: 0; }
.club-map-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
.club-map-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.club-form-hint { font-size: 11px; color: var(--muted); }
.club-form-actions { display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }
@media (max-width: 640px) { .club-form-card { padding: 16px; } .club-location-map { height: 280px; } }
</style>
