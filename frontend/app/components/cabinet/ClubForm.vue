<script setup lang="ts">
import "leaflet/dist/leaflet.css"
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet"
import { useAdminApi } from "~/api/admin"
import { useAuth } from "~/composables/useAuth"

const props = defineProps<{
  mode: "create" | "edit"
  clubId?: string
  basePath: string
}>()

const DEFAULT_LAT = 41.2995
const DEFAULT_LNG = 69.2401

const adminApi = useAdminApi()
const { user } = useAuth()

const isAdmin = computed(() => user.value?.role === "ADMIN" || user.value?.role === "MODERATOR")

useHead({
  title: props.mode === "edit" ? "Muassasani tahrirlash" : "Yangi muassasa qo'shish",
})

const createDefaultForm = () => ({
  name: "",
  category: "GAMING_CLUB",
  description: "",
  phone: "",
  email: "",
  website: "",
  address: "",
  latitude: null as number | null,
  longitude: null as number | null,
  status: isAdmin.value ? "ACTIVE" : "DRAFT",
  is_verified: false,
})

const form = ref(createDefaultForm())
const logoFile = ref<File | null>(null)
const logoPreview = ref("")

const isLoading = ref(props.mode === "edit")
const isSaving = ref(false)
const errorMessage = ref("")

const mapEl = ref<HTMLElement | null>(null)
let mapInstance: LeafletMap | null = null
let markerInstance: LeafletMarker | null = null

const onLogoChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  logoFile.value = file
  logoPreview.value = URL.createObjectURL(file)
}

const loadClub = async () => {
  if (!props.clubId) return
  isLoading.value = true
  errorMessage.value = ""
  try {
    const club = await adminApi.getClub(props.clubId)
    form.value = {
      name: club.name || "",
      category: club.category || "GAMING_CLUB",
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
    if (club.logo) logoPreview.value = club.logo
  } catch (err: any) {
    errorMessage.value = err?.data?.message || err?.message || "Klub ma'lumotlarini yuklashda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const setMarkerPosition = (lat: number, lng: number) => {
  form.value.latitude = lat
  form.value.longitude = lng
  markerInstance?.setLatLng([lat, lng])
}

const initMap = async () => {
  if (!mapEl.value) return

  const L = (await import("leaflet")).default
  const [{ default: iconUrl }, { default: iconRetinaUrl }, { default: shadowUrl }] = await Promise.all([
    import("leaflet/dist/images/marker-icon.png"),
    import("leaflet/dist/images/marker-icon-2x.png"),
    import("leaflet/dist/images/marker-shadow.png"),
  ])
  delete (L.Icon.Default.prototype as any)._getIconUrl
  L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl })

  const lat = form.value.latitude ?? DEFAULT_LAT
  const lng = form.value.longitude ?? DEFAULT_LNG

  mapInstance = L.map(mapEl.value).setView([lat, lng], 13)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(mapInstance)

  markerInstance = L.marker([lat, lng], { draggable: true }).addTo(mapInstance)
  form.value.latitude = lat
  form.value.longitude = lng

  markerInstance.on("dragend", () => {
    const pos = markerInstance!.getLatLng()
    setMarkerPosition(pos.lat, pos.lng)
  })

  mapInstance.on("click", (event: any) => {
    setMarkerPosition(event.latlng.lat, event.latlng.lng)
  })
}

const buildPayload = () => {
  const data = new FormData()
  data.append("name", form.value.name.trim())
  data.append("category", form.value.category)
  data.append("description", form.value.description)
  data.append("phone", form.value.phone)
  data.append("email", form.value.email)
  data.append("website", form.value.website)
  data.append("address", form.value.address)
  if (form.value.latitude != null) data.append("latitude", form.value.latitude.toFixed(6))
  if (form.value.longitude != null) data.append("longitude", form.value.longitude.toFixed(6))
  data.append("status", form.value.status)
  if (isAdmin.value) data.append("is_verified", form.value.is_verified ? "true" : "false")
  if (logoFile.value) data.append("logo", logoFile.value)
  return data
}

const save = async () => {
  if (!form.value.name.trim()) {
    errorMessage.value = "Klub nomini kiriting"
    return
  }

  isSaving.value = true
  errorMessage.value = ""
  try {
    const payload = buildPayload()
    if (props.mode === "edit" && props.clubId) {
      await adminApi.updateClub(props.clubId, payload)
    } else {
      await adminApi.createClub(payload)
    }
    await navigateTo(props.basePath)
  } catch (err: any) {
    errorMessage.value = err?.data?.message || err?.message || "Saqlashda xatolik yuz berdi"
  } finally {
    isSaving.value = false
  }
}

const cancel = () => navigateTo(props.basePath)

onMounted(async () => {
  if (props.mode === "edit") await loadClub()
  await initMap()
})

onUnmounted(() => {
  mapInstance?.remove()
  mapInstance = null
  markerInstance = null
})
</script>

<template>
  <div class="admin-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">
          {{ mode === "edit" ? "Muassasani tahrirlash" : "Yangi muassasa qo'shish" }}
        </h1>
        <p class="page-subtitle">Muassasa haqida to'liq ma'lumotlarni kiriting</p>
      </div>
    </div>

    <div v-if="isLoading" class="loading-box">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <form v-else class="form-card" @submit.prevent="save">
      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

      <div class="form-row">
        <div class="form-group">
          <label>Nomi *</label>
          <input v-model="form.name" type="text" placeholder="Masalan: Galaxy Gaming / Gentleman Salon" required>
        </div>
        <div class="form-group">
          <label>Toifa *</label>
          <select v-model="form.category" required>
            <option value="GAMING_CLUB">🎮 O'yin klubi (Gaming Club)</option>
            <option value="BARBERSHOP">💈 Sartaroshxona (Barbershop)</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>Tavsifi</label>
        <textarea v-model="form.description" rows="3" placeholder="Klub haqida qisqacha ma'lumot..." />
      </div>

      <div class="form-group">
        <label>Rasmi</label>
        <input type="file" accept="image/jpeg,image/png,image/webp" @change="onLogoChange">
        <img v-if="logoPreview" :src="logoPreview" alt="Klub rasmi" class="logo-preview">
      </div>

      <div class="form-group">
        <label>Lokatsiyasi</label>
        <input v-model="form.address" type="text" placeholder="Manzilni qo'lda kiriting (ko'cha, uy, mo'ljal...)">
        <div ref="mapEl" class="location-map" />
        <p class="map-hint">Xaritada bosib yoki belgini sudrab aniq joyni ko'rsating.</p>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Telefon raqami</label>
          <input v-model="form.phone" type="tel" placeholder="+998 90 123 45 67">
        </div>
        <div class="form-group">
          <label>Email</label>
          <input v-model="form.email" type="email" placeholder="info@club.uz">
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Vebsayti</label>
          <input v-model="form.website" type="url" placeholder="https://club.uz">
        </div>
        <div class="form-group">
          <label>Holati</label>
          <select v-model="form.status">
            <option value="DRAFT">DRAFT (Qoralama)</option>
            <option value="PENDING">PENDING (Kutilmoqda)</option>
            <template v-if="isAdmin">
              <option value="ACTIVE">ACTIVE (Faol)</option>
              <option value="SUSPENDED">SUSPENDED (Muzlatilgan)</option>
              <option v-if="mode === 'edit'" value="ARCHIVED">ARCHIVED (Arxivlangan)</option>
            </template>
          </select>
        </div>
      </div>

      <div v-if="isAdmin" class="form-checkbox">
        <label>
          <input v-model="form.is_verified" type="checkbox">
          <span>Tekshiruvdan o'tgan deb belgilash (Verified badge)</span>
        </label>
      </div>

      <div class="form-actions">
        <button type="button" class="secondary-button" @click="cancel">
          Bekor qilish
        </button>
        <button type="submit" class="primary-button" :disabled="isSaving">
          {{ isSaving ? "Saqlanmoqda..." : "Saqlash" }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 800;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.loading-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px;
  gap: 12px;
  color: var(--muted);
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.form-group input, .form-group textarea, .form-group select {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 13px;
}

.form-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.form-checkbox label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
}

.form-error {
  margin: 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  font-size: 12px;
}

.logo-preview {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--border);
  margin-top: 6px;
}

.location-map {
  height: 280px;
  border-radius: 10px;
  border: 1px solid var(--border);
  overflow: hidden;
  margin-top: 4px;
}

.map-hint {
  margin: 0;
  font-size: 11px;
  color: var(--muted);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}
</style>
