<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
import FreeModeToggle from "~/components/cabinet/FreeModeToggle.vue"
import type { ServiceTypeManagementItem } from "~/api/serviceTypes"
import { descendantServiceIds, serviceTreeOptions } from "~/utils/serviceTree"
import ServiceChecklist from "~/components/cabinet/ServiceChecklist.vue"

definePageMeta({
  alias: ["/site/staff/panel/branches", "/site/client/panel/branches"],
  layout: "admin",
  middleware: ["admin"],
})

useHead({
  title: "Filiallar va Zonalar",
})

const route = useRoute()
const cabinetPath = useCabinetPath()
const adminApi = useAdminApi()
const { isStaff } = useCabinetAccess()
const { statusLabel } = useCabinetLabels()

const clubs = ref<any[]>([])
const branches = ref<any[]>([])
const cities = ref<any[]>([])
const services = ref<ServiceTypeManagementItem[]>([])
const selectedClubId = ref(typeof route.query.club_id === "string" ? route.query.club_id : "")
const selectedBranch = ref<any>(null)
const branchZones = ref<any[]>([])

const isLoading = ref(true)
const isZonesLoading = ref(false)
const errorMessage = ref("")

// Branch Modal
const showBranchModal = ref(false)
const editingBranch = ref<any>(null)
const isSavingBranch = ref(false)
const branchModalError = ref("")
const branchForm = ref({
  club: "",
  enabled_services: [] as string[],
  name: "",
  city: "",
  district: "",
  address: "",
  phone: "",
  latitude: null as number | null,
  longitude: null as number | null,
  status: "ACTIVE",
  is_24_hours: true,
})

const branchClub = computed(() => clubs.value.find(item => item.id === branchForm.value.club))
const primaryService = computed(() => services.value.find(service => service.id === branchClub.value?.service_type))
const branchServiceChoices = computed(() => {
  const roots = [...(branchClub.value?.available_services || []), ...(primaryService.value ? [primaryService.value.id] : [])]
  const allowed = descendantServiceIds(services.value, roots)
  return services.value.filter(service => service.is_active && allowed.has(service.id) && service.id !== primaryService.value?.id)
})
const branchLogo = ref<File | null>(null)
const branchPhotos = ref<File[]>([])
const photoPreviews = ref<string[]>([])
const logoPreview = ref("")
const clearUploads = () => {
  photoPreviews.value.forEach(url => URL.revokeObjectURL(url))
  if (logoPreview.value.startsWith("blob:")) URL.revokeObjectURL(logoPreview.value)
  photoPreviews.value = []; logoPreview.value = ""
  branchLogo.value = null; branchPhotos.value = []
}
onBeforeUnmount(clearUploads)
const pickBranchImages = (event: Event, kind: "logo" | "photos") => {
  const input = event.target as HTMLInputElement
  const files = [...(input.files || [])]
  if (!files.length) return
  if (files.length > 10 || files.some(file => !["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024)) {
    branchModalError.value = "JPG, PNG yoki WEBP rasmlar tanlang: har biri 5 MB gacha, ko‘pi bilan 10 ta."
    input.value = ""; return
  }
  branchModalError.value = ""
  if (kind === "logo") {
    if (logoPreview.value.startsWith("blob:")) URL.revokeObjectURL(logoPreview.value)
    branchLogo.value = files[0] || null
    logoPreview.value = branchLogo.value ? URL.createObjectURL(branchLogo.value) : ""
  } else {
    photoPreviews.value.forEach(url => URL.revokeObjectURL(url))
    branchPhotos.value = files
    photoPreviews.value = files.map(file => URL.createObjectURL(file))
  }
}
const zoneServiceChoices = computed(() => {
  const allowed = descendantServiceIds(services.value, selectedBranch.value?.enabled_services || [])
  return serviceTreeOptions(services.value.filter(service => service.is_active && allowed.has(service.id)))
})
watch(() => branchForm.value.club, () => {
  const allowed = new Set(branchServiceChoices.value.map(service => service.id))
  branchForm.value.enabled_services = branchForm.value.enabled_services.filter(id => allowed.has(id))
  if (primaryService.value?.is_active) branchForm.value.enabled_services.push(primaryService.value.id)
}, { flush: "sync" })

const { districts, isDistrictLoading, districtError } = useCityDistricts(() => branchForm.value.city)

// Zone Modal
const showZoneModal = ref(false)
const editingZone = ref<any>(null)
const isSavingZone = ref(false)
const zoneModalError = ref("")
const zoneForm = ref({
  branch: "",
  name: "",
  service_type: "",
  resource_type: "GENERAL",
  booking_type: "PER_SEAT",
  capacity: 10,
  unit_count: 10,
  price_per_hour_tiyin: 2000000,
  status: "ACTIVE",
})

watch(() => zoneForm.value.service_type, id => {
  const code = services.value.find(service => service.id === id)?.code
  if (code && ["COMPUTER", "PLAYSTATION", "BILLIARDS"].includes(code)) zoneForm.value.resource_type = code
})

const fetchData = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const [clubsRes, citiesRes, serviceRes] = await Promise.all([
      adminApi.getClubs({ page_size: 100 }),
      adminApi.getCities(),
      adminApi.getServiceTypes(),
    ])
    clubs.value = clubsRes.results || clubsRes.data || clubsRes || []
    if (selectedClubId.value && !clubs.value.some(club => club.id === selectedClubId.value)) {
      clubs.value.push(await adminApi.getClub(selectedClubId.value))
    }
    services.value = serviceRes
    cities.value = citiesRes.results || citiesRes.data || citiesRes || []

    await fetchBranches()
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

watch(() => route.query.club_id, () => {
  selectedClubId.value = typeof route.query.club_id === "string" ? route.query.club_id : ""
  void fetchBranches()
})

let branchLoadVersion = 0
let zoneLoadVersion = 0
const fetchBranches = async () => {
  const version = ++branchLoadVersion
  isLoading.value = true
  try {
    const params: Record<string, any> = { page_size: 100 }
    if (selectedClubId.value) params.club_id = selectedClubId.value

    const res = await adminApi.getBranches(params)
    if (version !== branchLoadVersion) return
    branches.value = res.results || res.data || res || []
    if (!branches.value.some(branch => branch.id === selectedBranch.value?.id)) {
      selectedBranch.value = null
      branchZones.value = []
      zoneLoadVersion++
      if (branches.value.length) void selectBranch(branches.value[0])
    }
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const selectBranch = async (branch: any) => {
  const version = ++zoneLoadVersion
  selectedBranch.value = branch
  isZonesLoading.value = true
  try {
    const res = await adminApi.getZones({ branch_id: branch.id })
    if (version !== zoneLoadVersion) return
    branchZones.value = res.results || res.data || res || []
  } catch (err) {
    console.error("Failed to load zones", err)
  } finally {
    if (version === zoneLoadVersion) isZonesLoading.value = false
  }
}

const openCreateBranchModal = () => {
  clearUploads()
  editingBranch.value = null
  branchForm.value = {
    club: selectedClubId.value || (clubs.value[0]?.id || ""),
    enabled_services: [...(clubs.value.find(club => club.id === (selectedClubId.value || clubs.value[0]?.id))?.available_services || [])],
    name: "",
    city: "",
    district: "",
    address: "",
    phone: "",
    latitude: null as number | null,
    longitude: null as number | null,
    status: "ACTIVE",
    is_24_hours: true,
  }
  branchModalError.value = ""
  showBranchModal.value = true
}

const openEditBranchModal = (b: any) => {
  clearUploads()
  logoPreview.value = b.logo || ""
  editingBranch.value = b
  branchForm.value = {
    club: b.club?.id || b.club || "",
    enabled_services: [...(b.enabled_services || [])],
    name: b.name,
    city: b.city?.id || b.city || "",
    district: b.district?.id || b.district || "",
    address: b.address,
    phone: b.phone || "",
    latitude: b.latitude != null ? Number(b.latitude) : null,
    longitude: b.longitude != null ? Number(b.longitude) : null,
    status: b.status || "ACTIVE",
    is_24_hours: b.is_24_hours ?? true,
  }
  branchModalError.value = ""
  showBranchModal.value = true
}

const saveBranch = async () => {
  if (!branchForm.value.name.trim() || !branchForm.value.address.trim()) {
    branchModalError.value = "Filial nomi va manzilini kiriting"
    return
  }
  const latitude = branchForm.value.latitude
  const longitude = branchForm.value.longitude
  if (latitude == null || longitude == null || String(latitude) === "" || String(longitude) === "" || !Number.isFinite(Number(latitude)) || !Number.isFinite(Number(longitude)) || Math.abs(Number(latitude)) > 90 || Math.abs(Number(longitude)) > 180) {
    branchModalError.value = "Latitude (−90…90) va longitude (−180…180) qiymatlarini kiriting."
    return
  }
  isSavingBranch.value = true
  branchModalError.value = ""
  try {
    const payload = new FormData()
    const enabled = new Set(branchForm.value.enabled_services)
    if (primaryService.value?.is_active) enabled.add(primaryService.value.id)
    Object.entries(branchForm.value).forEach(([key, value]) => {
      if (key !== "enabled_services" && value != null) payload.append(key, String(value))
    })
    enabled.forEach(id => payload.append("enabled_services", id))
    if (branchLogo.value) payload.append("logo", branchLogo.value)
    branchPhotos.value.forEach(file => payload.append("photos", file))
    if (editingBranch.value) {
      await adminApi.updateBranch(editingBranch.value.id, payload)
    } else {
      await adminApi.createBranch(payload)
    }
    showBranchModal.value = false
    clearUploads()
    selectedBranch.value = null
    await fetchBranches()
  } catch (err: any) {
    branchModalError.value = err?.data?.message || err?.message || "Saqlashda xatolik yuz berdi"
  } finally {
    isSavingBranch.value = false
  }
}

const openCreateZoneModal = () => {
  if (!selectedBranch.value) return
  editingZone.value = null
  zoneForm.value = {
    branch: selectedBranch.value.id,
    name: "",
    service_type: "",
  resource_type: "GENERAL",
    booking_type: "PER_SEAT",
    capacity: 10,
    unit_count: 10,
    price_per_hour_tiyin: 2000000,
    status: "ACTIVE",
  }
  zoneModalError.value = ""
  showZoneModal.value = true
}

const openEditZoneModal = (z: any) => {
  editingZone.value = z
  zoneForm.value = {
    branch: selectedBranch.value.id,
    name: z.name,
    service_type: z.service_type || "",
    resource_type: z.resource_type || "GENERAL",
    booking_type: z.booking_type || "PER_SEAT",
    capacity: z.capacity || 10,
    unit_count: z.unit_count || 10,
    price_per_hour_tiyin: z.price_per_hour_tiyin ?? 2000000,
    status: z.status || "ACTIVE",
  }
  zoneModalError.value = ""
  showZoneModal.value = true
}

const saveZone = async () => {
  if (!zoneForm.value.name.trim()) {
    zoneModalError.value = "Zona nomini kiriting"
    return
  }
  isSavingZone.value = true
  zoneModalError.value = ""
  try {
    if (editingZone.value) {
      await adminApi.updateZone(editingZone.value.id, { ...zoneForm.value, service_type: zoneForm.value.service_type || null })
    } else {
      await adminApi.createZone({ ...zoneForm.value, service_type: zoneForm.value.service_type || null })
    }
    showZoneModal.value = false
    if (selectedBranch.value) {
      await selectBranch(selectedBranch.value)
    }
  } catch (err: any) {
    zoneModalError.value = err?.data?.message || err?.message || "Saqlashda xatolik yuz berdi"
  } finally {
    isSavingZone.value = false
  }
}

const deleteZone = async (z: any) => {
  if (!confirm(`"${z.name}" zonasini o'chirmoqchimisiz?`)) return
  try {
    await adminApi.deleteZone(z.id)
    if (selectedBranch.value) {
      await selectBranch(selectedBranch.value)
    }
  } catch (err) {
    console.error("Failed to delete zone", err)
  }
}

const formatPrice = (tiyin: number) => {
  const sum = Math.round((tiyin || 0) / 100)
  return new Intl.NumberFormat("uz-UZ").format(sum) + " so'm/soat"
}

onMounted(() => {
  void fetchData()
})
useDialogFocus(showBranchModal, "#cabinet-branches-showBranchModal", () => { showBranchModal.value = false })
useDialogFocus(showZoneModal, "#cabinet-branches-showZoneModal", () => { showZoneModal.value = false })
</script>

<template>
  <div class="admin-page">
    <!-- Filter Bar -->
    <div class="filter-bar cabinet-list-toolbar">
      <div class="club-filter-select">
        <label>Klubni tanlang:</label>
        <select v-model="selectedClubId" @change="fetchBranches" aria-label="Xizmat">
          <option value="">Barcha klublar filiallari</option>
          <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <button v-if="isStaff" type="button" class="primary-button" @click="openCreateBranchModal">
        <CabinetIcon name="plus" /> Yangi filial qo‘shish
      </button>
    </div>

    <!-- Main Two-Column Layout -->
    <div class="branches-layout-grid">
      <!-- Left: Branches List -->
      <div class="branches-panel">
        <div class="panel-header">
          <h3>Filiallar ({{ branches.length }})</h3>
        </div>

        <div v-if="isLoading" class="loading-box">
          <span class="auth-spinner" />
        </div>

        <div v-else-if="!branches.length" class="empty-state">
          Filiallar topilmadi.
        </div>

        <div v-else class="branch-cards-list">
          <div
            v-for="b in branches"
            :key="b.id"
            class="branch-item-card"
            :class="{ 'is-selected': selectedBranch?.id === b.id }"
            @click="selectBranch(b)"
          >
            <div class="bic-top">
              <span class="bic-name">{{ b.name }}</span>
              <span class="status-badge" :class="b.status.toLowerCase()">{{ statusLabel(b.status) }}</span>
            </div>
            <NuxtLink v-if="clubs.find(club => club.id === (b.club?.id || b.club))?.category === 'BARBERSHOP'" :to="{ path: cabinetPath('/barbers'), query: { club_id: b.club?.id || b.club, branch_id: b.id } }" class="secondary-button" @click.stop>Sartaroshlar</NuxtLink>
            <p class="branch-services">{{ services.filter(service => (b.enabled_services || []).includes(service.id)).map(service => service.name).join(" · ") }}</p>
            <p class="bic-address"><CabinetIcon name="location" /> {{ b.address }}</p>
            <div class="bic-footer">
              <span class="bic-phone"><CabinetIcon name="phone" /> {{ b.phone || "—" }}</span>
              <div class="bic-actions" @click.stop>
                <FreeModeToggle v-if="isStaff" kind="branch" :id="b.id" :name="b.name" :is-free="b.is_free" @changed="fetchBranches" />
                <button type="button" v-if="isStaff" class="action-btn" title="Tahrirlash" @click="openEditBranchModal(b)"><CabinetIcon name="edit" /></button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Selected Branch Zones -->
      <div class="zones-panel">
        <div v-if="!selectedBranch" class="empty-select-box">
          Filialni tanlang yoki yangi filial qo'shing.
        </div>

        <div v-else class="zones-content">
          <div class="zones-header">
            <div>
              <h3>{{ selectedBranch.name }} — Zonalar</h3>
              <p class="zones-sub">Xona va joylar konfiguratsiyasi</p>
            </div>
            <button type="button" v-if="isStaff" class="primary-button add-zone-btn" @click="openCreateZoneModal">
              <span><CabinetIcon name="plus" /> Zona qo'shish</span>
            </button>
          </div>

          <div v-if="isZonesLoading" class="loading-box">
            <span class="auth-spinner" />
          </div>

          <div v-else-if="!branchZones.length" class="empty-state">
            Ushbu filialda zonalar mavjud emas. Yangi zona qo'shing.
          </div>

          <div v-else class="zones-grid">
            <div v-for="z in branchZones" :key="z.id" class="zone-manage-card">
              <div class="zmc-header">
                <span class="zmc-type-icon">{{ z.resource_type === 'COMPUTER' ? '' : '' }}</span>
                <span class="status-badge" :class="z.status.toLowerCase()">{{ statusLabel(z.status) }}</span>
              </div>
              <h4 class="zmc-title">{{ z.name }}</h4><span v-if="z.service_type_name" class="spec-tag">{{ z.service_type_name }}</span>
              <div class="zmc-specs">
                <span class="spec-tag"> Sig'im: {{ z.capacity }} kishi</span>
                <span class="spec-tag"> Joylar: {{ z.unit_count }} dona</span>
                <span class="spec-tag">{{ z.booking_type === 'PER_SEAT' ? 'Har bir joy' : 'Butun xona' }}</span>
              </div>
              <div class="zmc-price">
                {{ formatPrice(z.price_per_hour_tiyin) }}
              </div>
              <div v-if="isStaff" class="zmc-footer">
                <button type="button" class="action-btn" @click="openEditZoneModal(z)"><CabinetIcon name="edit" /> Tahrirlash</button>
                <button type="button" class="action-btn delete" @click="deleteZone(z)"><CabinetIcon name="delete" /> O'chirish</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Branch Modal -->
    <Teleport to="body">
      <div v-if="showBranchModal" id="cabinet-branches-showBranchModal" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" aria-label="Tahrirlash" tabindex="-1" @click.self="showBranchModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>{{ editingBranch ? 'Filialni tahrirlash' : 'Yangi filial qo‘shish' }}</h3>
            <button type="button" class="modal-close-btn" @click="showBranchModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="saveBranch">
            <p v-if="branchModalError" class="form-error">{{ branchModalError }}</p>

            <div class="form-group">
              <label>Muassasa *</label>
              <select v-model="branchForm.club" required aria-label="Tanlash">
                <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>

            <div class="form-group">
              <label>Filial nomi *</label>
              <input v-model="branchForm.name" type="text" placeholder="Masalan: Chilonzor filiali" required aria-label="Masalan: Chilonzor filiali">
            </div>

            <div v-if="primaryService" class="primary-service-label">{{ primaryService.name }}</div>
            <fieldset v-if="branchServiceChoices.length" class="service-picker"><legend>Qo‘shimcha xizmatlar</legend><ServiceChecklist v-model="branchForm.enabled_services" :services="branchServiceChoices" /></fieldset>
            <div class="form-row">
              <div class="form-group">
                <label>Shahar *</label>
                <select v-model="branchForm.city" required @change="branchForm.district = ''" aria-label="Tanlash">
                  <option value="" disabled>Shaharni tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>Tuman *</label>
                <select v-model="branchForm.district" aria-label="Tuman" required :disabled="isDistrictLoading || !branchForm.city">
                  <option value="" disabled>{{ isDistrictLoading ? "Yuklanmoqda…" : "Tumanni tanlang" }}</option>
                  <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
                <small v-if="districtError" role="alert">{{ districtError }}</small>
                <small v-else-if="branchForm.city && !isDistrictLoading && !districts.length">Bu hudud uchun tumanlar hali qo‘shilmagan.</small>
              </div>
            </div>

            <div class="form-group">
              <label>Manzil *</label>
              <input v-model="branchForm.address" type="text" placeholder="Ko'cha va uy raqami" required aria-label="Ko'cha va uy raqami">
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Filial telefoni</label>
                <input v-model="branchForm.phone" type="tel" placeholder="+998 90 123 45 67">
              </div>
              <div class="form-group">
                <label>Holat</label>
                <select v-model="branchForm.status" aria-label="Tanlash">
                  <option value="ACTIVE">Faol</option>
                  <option value="INACTIVE">Nofaol</option>
                </select>
              </div>
            </div>

            <div class="form-row branch-coordinates">
              <div class="form-group"><label for="branch-latitude">Latitude *</label><input id="branch-latitude" v-model.number="branchForm.latitude" type="number" required min="-90" max="90" step="0.000001" inputmode="decimal" placeholder="41.311081"></div>
              <div class="form-group"><label for="branch-longitude">Longitude *</label><input id="branch-longitude" v-model.number="branchForm.longitude" type="number" required min="-180" max="180" step="0.000001" inputmode="decimal" placeholder="69.240562"></div>
            </div>
            <div class="branch-media-fields">
              <div class="form-group"><label for="branch-logo">Filial logotipi</label><img v-if="logoPreview" :src="logoPreview" class="branch-logo-preview" alt="Filial logotipi"><input id="branch-logo" type="file" accept="image/jpeg,image/png,image/webp" @change="pickBranchImages($event, 'logo')"></div>
              <div class="form-group"><label for="branch-photos">Filial rasmlari</label><div v-if="editingBranch?.images?.length || photoPreviews.length" class="branch-photo-previews"><img v-for="image in editingBranch?.images || []" :key="image.id" :src="image.image" alt="Filial rasmi"><img v-for="url in photoPreviews" :key="url" :src="url" alt="Yangi rasm"></div><input id="branch-photos" type="file" multiple accept="image/jpeg,image/png,image/webp" @change="pickBranchImages($event, 'photos')"><small>JPG, PNG, WEBP · Har biri 5 MB gacha</small></div>
            </div>

            <div class="form-checkbox">
              <label>
                <input v-model="branchForm.is_24_hours" type="checkbox">
                <span>24/7 rejimida ishlaydi</span>
              </label>
            </div>

            <div class="modal-actions">
              <button type="button" class="secondary-button" @click="showBranchModal = false">Bekor qilish</button>
              <button type="submit" class="primary-button" :disabled="isSavingBranch || isDistrictLoading">{{ isSavingBranch ? "Saqlanmoqda..." : "Saqlash" }}</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Zone Modal -->
    <Teleport to="body">
      <div v-if="showZoneModal" id="cabinet-branches-showZoneModal" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" aria-label="Tahrirlash" tabindex="-1" @click.self="showZoneModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>{{ editingZone ? 'Zonani tahrirlash' : 'Yangi zona qo‘shish' }}</h3>
            <button type="button" class="modal-close-btn" @click="showZoneModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="saveZone">
            <p v-if="zoneModalError" class="form-error">{{ zoneModalError }}</p>

            <div class="form-group">
              <label>Zona nomi *</label>
              <input v-model="zoneForm.name" type="text" placeholder="Masalan: 1-stol, maydon yoki xona" required aria-label="Masalan: 1-stol, maydon yoki xona">
            </div>

            <div class="form-group"><label for="zone-service">Xizmat turi</label><select id="zone-service" v-model="zoneForm.service_type"><option value="">Umumiy</option><option v-for="service in zoneServiceChoices" :key="service.id" :value="service.id">{{ service.label }}</option></select></div>
            <div class="form-row">
              <div class="form-group">
                <label>Resurs turi</label>
                <select v-model="zoneForm.resource_type" aria-label="Tanlash">
                  <option value="GENERAL">Resurs</option>
                  <option value="COMPUTER"> Computer (Kompyuter)</option>
                  <option value="PLAYSTATION"> PlayStation</option><option value="BILLIARDS">Bilyard</option>
                </select>
              </div>
              <div class="form-group">
                <label>Bronlash turi</label>
                <select v-model="zoneForm.booking_type" aria-label="Tanlash">
                  <option value="PER_SEAT">Har bir joy uchun</option>
                  <option value="PER_ZONE">Butun resurs uchun</option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Sig'im (odam soni)</label>
                <input v-model.number="zoneForm.capacity" type="number" min="1" max="500" required>
              </div>
              <div class="form-group">
                <label>Joylar (kompyuterlar) soni</label>
                <input v-model.number="zoneForm.unit_count" type="number" min="1" max="500" required>
              </div>
            </div>

            <div class="form-group">
              <label>Soatlik narx (tiyinda, masalan: 2000000 = 20,000 so'm) *</label>
              <input v-model.number="zoneForm.price_per_hour_tiyin" type="number" min="0" step="1" required>
            </div>

            <div class="form-group">
              <label>Holat</label>
              <select v-model="zoneForm.status" aria-label="Tanlash">
                <option value="ACTIVE">Faol</option>
                <option value="INACTIVE">Nofaol</option>
              </select>
            </div>

            <div class="modal-actions">
              <button type="button" class="secondary-button" @click="showZoneModal = false">Bekor qilish</button>
              <button type="submit" class="primary-button" :disabled="isSavingZone">{{ isSavingZone ? "Saqlanmoqda..." : "Saqlash" }}</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.cabinet-modal .form-row.branch-coordinates { flex-direction: row; }
.branch-coordinates input { width: 100%; min-width: 0; }
.primary-service-label { width: fit-content; padding: 7px 12px; border-radius: 8px; color: var(--accent); background: var(--control); font-size: 13px; font-weight: 600; }
.branch-media-fields { display: grid; gap: 18px; padding-top: 16px; border-top: 1px solid var(--border); }
.branch-logo-preview { width: 64px; height: 64px; object-fit: cover; border: 1px solid var(--border); border-radius: 12px; }
.branch-photo-previews { display: flex; flex-wrap: wrap; gap: 8px; }
.branch-photo-previews img { width: 80px; height: 64px; object-fit: cover; border-radius: 8px; }
.branch-media-fields input[type="file"] { max-width: 100%; font-size: 12px; padding: 10px; }
.branch-media-fields small { color: var(--muted); font-size: 11px; }

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

.filter-bar {
  padding: 14px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
}

.club-filter-select {
  display: flex;
  align-items: center;
  gap: 12px;
}

.club-filter-select label {
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.club-filter-select select {
  flex: 1;
  max-width: 320px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 13px;
}

.branches-layout-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 20px;
  align-items: start;
}

.branches-panel, .zones-panel {
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  padding: 20px;
  min-height: 480px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
}

.branch-cards-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.branch-item-card {
  padding: 14px;
  background: var(--control);
  border: 1px solid var(--border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.branch-item-card:hover {
  border-color: var(--accent);
}

.branch-item-card.is-selected {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--control));
}

.bic-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.bic-name {
  font-weight: 700;
  font-size: 14px;
}

.bic-address {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.bic-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.bic-phone {
  color: var(--muted);
}

.zones-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.zones-header h3 {
  margin: 0 0 2px;
  font-size: 17px;
  font-weight: 750;
}

.zones-sub {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.add-zone-btn {
  padding: 6px 14px;
  font-size: 12px;
}

.zones-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.zone-manage-card {
  padding: 16px;
  background: var(--control);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.zmc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.zmc-type-icon {
  font-size: 20px;
}

.zmc-title {
  margin: 0;
  font-size: 15px;
  font-weight: 750;
}

.zmc-specs {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.spec-tag {
  font-size: 11px;
  color: var(--muted);
}

.zmc-price {
  font-size: 14px;
  font-weight: 800;
  color: var(--accent);
}

.zmc-footer {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
}

.status-badge.active { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-badge.inactive, .status-badge.disabled { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.status-badge.maintenance { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }

.action-btn {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--control);
  cursor: pointer;
  font-size: 12px;
}

.action-btn.delete:hover {
  border-color: #ef4444;
  color: #ef4444;
}

.empty-select-box, .empty-state {
  padding: 60px 20px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.loading-box {
  display: flex;
  justify-content: center;
  padding: 40px;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
}

.modal-card {
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  width: min(100%, 520px);
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 16px;
  color: var(--muted);
  cursor: pointer;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.form-group input, .form-group select {
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
}

.form-checkbox input[type="checkbox"] { width: 18px; height: 18px; min-height: 18px; flex: 0 0 18px; margin: 0; padding: 0; accent-color: var(--accent); }

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

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}

@media (max-width: 900px) {
  .branches-layout-grid {
    grid-template-columns: 1fr;
  }
}
</style>
