<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
import type { ServiceTypeManagementItem } from "~/api/serviceTypes"
import { descendantServiceIds, rootService, serviceTreeOptions } from "~/utils/serviceTree"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faArrowLeft, faImage, faPlus, faXmark } from "@fortawesome/free-solid-svg-icons"

const props = defineProps<{ clubId?: string }>()

const MAX_IMAGE_SIZE = 5 * 1024 * 1024
const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]

const route = useRoute()
const cabinetPath = useCabinetPath()
const adminApi = useAdminApi()
const { isStaff: isPlatformAdmin } = useCabinetAccess()

const isEdit = computed(() => Boolean(props.clubId))
const listPath = computed(() => ({ path: cabinetPath("/clubs"), query: typeof route.query.service_type === "string" ? { service_type: route.query.service_type, status: "ACTIVE" } : {} }))


const loadedCategory = ref("")
const services = ref<ServiceTypeManagementItem[]>([])
const serviceChoices = computed(() => {
  const scope = !isEdit.value && typeof route.query.service_type === "string" ? descendantServiceIds(services.value, [route.query.service_type]) : null
  return serviceTreeOptions(services.value.filter(service => service.is_active && (!scope || scope.has(service.id))))
})
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

const selectedService = computed(() => services.value.find(service => service.id === (form.value.service_type || route.query.service_type)) || null)
const serviceName = computed(() => selectedService.value?.name || "Muassasa")
const formTitle = computed(() => `${serviceName.value} ${isEdit.value ? 'ma’lumotlarini tahrirlash' : 'qo‘shish'}`)
const isBarbershop = computed(() => rootService(services.value, selectedService.value)?.code.toUpperCase() === "BARBERSHOP" || loadedCategory.value === "BARBERSHOP")
const hasServiceContext = computed(() => typeof route.query.service_type === "string" && services.value.some(service => service.id === route.query.service_type))
const includedServices = computed(() => {
  if (!selectedService.value) return []
  const scope = descendantServiceIds(services.value, [selectedService.value.id])
  return services.value.filter(service => service.is_active && scope.has(service.id))
})
const additionalServiceOptions = computed(() => includedServices.value.filter(service => service.id !== form.value.service_type))
const selectedAdditionalServices = computed(() => additionalServiceOptions.value.filter(service => form.value.available_services.includes(service.id)))
const addService = (event: Event) => {
  const select = event.target as HTMLSelectElement
  const id = select.value
  if (additionalServiceOptions.value.some(service => service.id === id) && !form.value.available_services.includes(id)) {
    form.value.available_services.push(id)
  }
  select.value = ""
}
const removeService = (id: string) => { form.value.available_services = form.value.available_services.filter(value => value !== id) }
useHead({ title: formTitle })

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
  loadedCategory.value = club.category || ""
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
  data.append("latitude", f.latitude == null ? "" : f.latitude.toFixed(6))
  data.append("longitude", f.longitude == null ? "" : f.longitude.toFixed(6))
  data.append("status", f.status)
  data.append("is_verified", f.is_verified ? "true" : "false")
  if (logoFile.value) data.append("logo", logoFile.value)
  if (coverFile.value) data.append("cover", coverFile.value)
  return data
}

const coordinateValue = (value: unknown, limit: number): number | null | undefined => {
  if (value == null || value === "") return null
  const number = Number(value)
  return Number.isFinite(number) && Math.abs(number) <= limit ? number : undefined
}

const save = async () => {
  if (isSaving.value) return
  if (!form.value.name.trim()) {
    errorMessage.value = "Xizmat nomini kiriting"
    return
  }
  const latitude = coordinateValue(form.value.latitude, 90)
  const longitude = coordinateValue(form.value.longitude, 180)
  if (latitude === undefined || longitude === undefined) {
    errorMessage.value = "Latitude −90 dan 90 gacha, longitude −180 dan 180 gacha son bo‘lishi kerak."
    return
  }
  if (latitude === null || longitude === null) {
    errorMessage.value = "Latitude va longitude qiymatlarini kiritish majburiy."
    return
  }
  form.value.latitude = latitude
  form.value.longitude = longitude
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
      if (typeof route.query.service_type === "string" && services.value.some(service => service.id === route.query.service_type && service.is_active)) {
        form.value.service_type = route.query.service_type
        form.value.available_services = [route.query.service_type]
      }
      form.value.is_verified = Boolean(isPlatformAdmin.value)
      if (isPlatformAdmin.value && typeof route.query.owner === "string") form.value.owner = route.query.owner
    }
  } catch (error) {
    errorMessage.value = cabinetErrorMessage(error)
  } finally {
    isLoading.value = false
  }
})

onBeforeUnmount(() => {
  objectUrls.forEach(url => URL.revokeObjectURL(url))
})
</script>

<template>
  <div class="club-form-page">
    <header class="club-form-header">
      <NuxtLink :to="listPath" class="back-link" aria-label="Xizmatlarga qaytish"><FontAwesomeIcon :icon="faArrowLeft" /></NuxtLink>
      <h1>{{ formTitle }}</h1>
    </header>

    <nav v-if="isEdit && !isLoading" class="club-related-nav" aria-label="Muassasa bo‘limlari">
      <NuxtLink :to="{ path: cabinetPath('/branches'), query: { club_id: props.clubId } }">Filiallar</NuxtLink>
      <NuxtLink v-if="loadedCategory === 'BARBERSHOP'" :to="{ path: cabinetPath('/barbers'), query: { club_id: props.clubId } }">Sartaroshlar</NuxtLink>
      <NuxtLink :to="{ path: cabinetPath('/bookings'), query: { club_id: props.clubId } }">Bronlar</NuxtLink>
    </nav>
    <div v-if="isLoading" class="club-form-loading"><span class="auth-spinner" />Yuklanmoqda…</div>

    <form v-show="!isLoading" class="venue-form" :aria-busy="isSaving" @submit.prevent="save">
      <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>
      <div class="form-main">
        <section class="form-card" aria-labelledby="venue-details-title">
          <h2 id="venue-details-title">Asosiy ma’lumotlar</h2>
          <div class="field-grid">
            <div class="form-group"><label for="club-name">Nomi <span>*</span></label><input id="club-name" v-model="form.name" type="text" :placeholder="`${serviceName} nomi`" required maxlength="255"></div>
            <div class="form-group"><label for="club-phone">Telefon</label><input id="club-phone" v-model="form.phone" type="tel" autocomplete="tel" placeholder="+998 90 123 45 67" maxlength="20"></div>
          </div>
          <div v-if="!hasServiceContext || isEdit" class="form-group">
            <label for="club-service-type">Xizmat turi <span>*</span></label>
            <select id="club-service-type" v-model="form.service_type" :disabled="!isPlatformAdmin && isEdit" required><option value="" disabled>Tanlang</option><option v-for="service in serviceChoices" :key="service.id" :value="service.id">{{ service.label }}</option></select>
          </div>
          <div v-if="additionalServiceOptions.length" class="form-group">
            <label for="club-additional-service">Qo‘shimcha xizmatlar</label>
            <select id="club-additional-service" @change="addService"><option value="" selected disabled>Xizmat tanlang</option><option v-for="service in additionalServiceOptions" :key="service.id" :value="service.id" :disabled="form.available_services.includes(service.id)">{{ service.name }}</option></select>
            <div v-if="selectedAdditionalServices.length" class="selected-services">
              <span v-for="service in selectedAdditionalServices" :key="service.id" class="service-chip">{{ service.name }}<button type="button" :aria-label="`${service.name} xizmatini olib tashlash`" @click="removeService(service.id)"><FontAwesomeIcon :icon="faXmark" /></button></span>
            </div>
          </div>
          <div class="form-group"><label for="club-description">Qisqa tavsif</label><textarea id="club-description" v-model="form.description" rows="3" placeholder="Muassasa haqida qisqacha" /></div>
          <div v-if="!isBarbershop" class="field-grid">
            <div class="form-group"><label for="club-email">Email</label><input id="club-email" v-model="form.email" type="email" autocomplete="email" placeholder="info@example.uz"></div>
            <div class="form-group"><label for="club-website">Vebsayt</label><input id="club-website" v-model="form.website" type="url" placeholder="https://"></div>
          </div>
        </section>

        <section class="form-card" aria-labelledby="venue-location-title">
          <h2 id="venue-location-title">Manzil</h2>
          <div class="field-grid">
            <div class="form-group"><label for="billing-city">Shahar <span>*</span></label><select id="billing-city" v-model="form.billing_city" required :disabled="!isPlatformAdmin && isEdit" @change="form.billing_district = ''"><option value="" disabled>Shaharni tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option></select></div>
            <div class="form-group"><label for="billing-district">Tuman <span>*</span></label><select id="billing-district" v-model="form.billing_district" required :disabled="isDistrictLoading || !form.billing_city || (!isPlatformAdmin && isEdit)"><option value="" disabled>{{ isDistrictLoading ? 'Yuklanmoqda…' : 'Tumanni tanlang' }}</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option></select><small v-if="districtError" role="alert">{{ districtError }}</small><small v-else-if="form.billing_city && !isDistrictLoading && !districts.length">Bu shahar uchun tumanlar kiritilmagan.</small></div>
          </div>
          <div class="form-group"><label for="club-address">Ko‘cha va uy</label><input id="club-address" v-model="form.address" type="text" autocomplete="street-address" maxlength="300" placeholder="Masalan, Amir Temur ko‘chasi, 12"></div>
          <div class="field-grid coordinates-grid">
            <div class="form-group"><label for="club-latitude">Latitude <span>*</span></label><input id="club-latitude" v-model.number="form.latitude" type="number" required inputmode="decimal" min="-90" max="90" step="0.000001" placeholder="41.311081"></div>
            <div class="form-group"><label for="club-longitude">Longitude <span>*</span></label><input id="club-longitude" v-model.number="form.longitude" type="number" required inputmode="decimal" min="-180" max="180" step="0.000001" placeholder="69.240562"></div>
          </div>
        </section>
      </div>

      <div class="form-aside">
        <section class="form-card" aria-labelledby="venue-images-title">
          <h2 id="venue-images-title">Rasmlar</h2>
          <label class="cover-upload" for="club-cover">
            <img v-if="coverPreview" :src="coverPreview" alt="Muqova" class="cover-preview">
            <span v-else class="upload-placeholder"><FontAwesomeIcon :icon="faImage" /><span>Muqova yuklash</span></span>
            <span v-if="coverPreview" class="replace-image">Almashtirish</span>
            <input id="club-cover" class="file-input" type="file" accept="image/jpeg,image/png,image/webp" aria-label="Muqova yuklash" @change="pickImage($event, 'cover')">
          </label>
          <label class="logo-upload" for="club-logo">
            <span class="logo-thumbnail"><img v-if="logoPreview" :src="logoPreview" alt="Logotip"><FontAwesomeIcon v-else :icon="faPlus" /></span>
            <span class="logo-copy"><strong>Logotip</strong><small>{{ logoPreview ? 'Almashtirish' : 'Rasm tanlash' }}</small></span>
            <input id="club-logo" class="file-input" type="file" accept="image/jpeg,image/png,image/webp" aria-label="Logotip yuklash" @change="pickImage($event, 'logo')">
          </label>
          <small class="upload-hint">JPG, PNG, WEBP · 5 MB gacha</small>
        </section>

        <section class="form-card" aria-labelledby="venue-settings-title">
          <h2 id="venue-settings-title">Sozlamalar</h2>
          <template v-if="isPlatformAdmin">
            <div class="form-group"><div class="label-row"><label for="club-owner">Egasi</label><button type="button" class="text-button" :aria-expanded="showNewClient" aria-controls="new-owner-fields" @click="showNewClient = !showNewClient"><FontAwesomeIcon :icon="showNewClient ? faXmark : faPlus" />{{ showNewClient ? 'Yopish' : 'Yangi' }}</button></div><select id="club-owner" v-model="form.owner"><option :value="null">O‘zim</option><option v-for="client in clientsList" :key="client.id" :value="client.id">{{ client.profile?.full_name || client.username }}</option></select></div>
            <div v-if="showNewClient" id="new-owner-fields" class="inline-client-form">
              <div class="form-group"><label for="new-owner-name">Ism-familiya</label><input id="new-owner-name" v-model="newClient.full_name" maxlength="150" autocomplete="name"></div>
              <div class="form-group"><label for="new-owner-phone">Telefon</label><input id="new-owner-phone" v-model="newClient.phone" type="tel" autocomplete="tel"></div>
              <div class="form-group"><label for="new-owner-login">Login</label><input id="new-owner-login" v-model="newClient.username" maxlength="30" autocomplete="off" autocapitalize="none"></div>
              <div class="form-group"><label for="new-owner-password">Parol</label><input id="new-owner-password" v-model="newClient.password" type="password" maxlength="128" autocomplete="new-password"></div>
              <button type="button" class="secondary-button" :disabled="creatingClient" @click="createClientHere">{{ creatingClient ? 'Saqlanmoqda…' : 'Egani qo‘shish' }}</button>
            </div>
          </template>
          <div class="form-group"><label for="club-status">Holat</label><select id="club-status" v-model="form.status"><option value="ACTIVE">Faol</option><option value="INACTIVE">Nofaol</option></select></div>
          <label v-if="isPlatformAdmin" class="verified-control"><span>Tasdiqlangan</span><input v-model="form.is_verified" type="checkbox" role="switch" aria-label="Tasdiqlangan muassasa"></label>
        </section>
      </div>

      <footer class="club-form-actions"><NuxtLink :to="listPath" class="cancel-link">Bekor qilish</NuxtLink><button type="submit" class="primary-button save-button" :disabled="isSaving || creatingClient || isDistrictLoading">{{ isSaving ? 'Saqlanmoqda…' : isEdit ? 'Saqlash' : 'Qo‘shish' }}</button></footer>
    </form>
  </div>
</template>

<style scoped>
.club-form-page { width: 100%; max-width: 1120px; margin: 0 auto; padding-bottom: 16px; }
.club-form-header { display: flex; align-items: center; gap: 14px; margin-bottom: 26px; }
.club-form-header h1 { margin: 0; font-size: clamp(20px, 2.2vw, 26px); font-weight: 750; letter-spacing: -.035em; line-height: 1.25; }
.back-link { display: grid; place-items: center; width: 38px; height: 38px; flex-shrink: 0; border: 1px solid var(--border); border-radius: 12px; color: var(--muted); background: var(--surface); font-size: 14px; text-decoration: none; }
.back-link:hover { color: var(--accent); border-color: var(--accent); }
.club-related-nav { display: flex; flex-wrap: wrap; gap: 6px; margin: -10px 0 20px; }
.club-related-nav a { padding: 9px 14px; border: 1px solid var(--border); border-radius: 9px; color: var(--muted); background: var(--surface); text-decoration: none; font-size: 13px; }
.club-form-loading { display: flex; flex-direction: column; align-items: center; padding: 60px; gap: 12px; color: var(--muted); }
.venue-form { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 20px; align-items: start; }
.form-main, .form-aside { display: grid; gap: 20px; min-width: 0; }
.form-card { display: grid; gap: 18px; min-width: 0; padding: 24px; border: 1px solid var(--panel-border); border-radius: 16px; background: var(--surface); box-shadow: 0 2px 6px #0f172a03; }
.form-card h2 { margin: 0 0 2px; color: var(--text); font-size: 14px; font-weight: 750; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; min-width: 0; }
.form-group { display: grid; gap: 7px; align-content: start; min-width: 0; }
.form-group label { color: var(--muted); font-size: 12px; font-weight: 600; }
.form-group label > span { color: var(--accent); }
.form-group input, .form-group textarea, .form-group select { display: block; width: 100%; min-width: 0; min-height: 44px; margin: 0; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--control); color: var(--text); font: inherit; font-size: 13px; transition: border-color .15s, box-shadow .15s; }
.form-group input::placeholder, .form-group textarea::placeholder { color: var(--muted); opacity: .65; }
.form-group input:focus, .form-group textarea:focus, .form-group select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent); }
.form-group textarea { resize: vertical; min-height: 88px; }
.form-group select { cursor: pointer; padding-right: 24px; }
.form-group :disabled { opacity: .55; cursor: not-allowed; }
.form-group small { color: var(--muted); font-size: 11px; line-height: 1.5; }
.coordinates-grid input { font-variant-numeric: tabular-nums; }
.selected-services { display: flex; flex-wrap: wrap; gap: 6px; }
.service-chip { display: inline-flex; align-items: center; gap: 8px; padding: 5px 6px 5px 10px; border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent); border-radius: 8px; color: var(--accent); background: color-mix(in srgb, var(--accent) 7%, transparent); font-size: 12px; }
.service-chip button { display: grid; place-items: center; width: 28px; height: 28px; padding: 0; border: 0; border-radius: 6px; color: inherit; background: transparent; cursor: pointer; }
.service-chip button:hover { background: color-mix(in srgb, var(--accent) 12%, transparent); }
.cover-upload { position: relative; display: grid; place-items: center; min-height: 140px; overflow: hidden; border: 1px dashed color-mix(in srgb, var(--muted) 40%, transparent); border-radius: 12px; background: var(--control); cursor: pointer; }
.upload-placeholder { display: grid; justify-items: center; gap: 12px; padding: 20px; color: var(--muted); font-size: 12px; }
.upload-placeholder > svg { font-size: 26px; opacity: .55; }
.cover-preview { width: 100%; height: 150px; object-fit: cover; }
.replace-image { position: absolute; right: 8px; bottom: 8px; padding: 5px 8px; border-radius: 6px; color: white; background: #0f172abf; font-size: 11px; }
.file-input { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
.cover-upload:focus-within, .logo-upload:focus-within { outline: 2px solid var(--accent); outline-offset: 3px; }
.logo-upload { position: relative; display: flex; align-items: center; gap: 12px; border-radius: 10px; cursor: pointer; }
.logo-thumbnail { display: grid; place-items: center; width: 48px; height: 48px; flex-shrink: 0; overflow: hidden; border: 1px solid var(--border); border-radius: 12px; background: var(--control); color: var(--muted); font-size: 15px; }
.logo-thumbnail img { width: 100%; height: 100%; object-fit: cover; }
.logo-copy { display: grid; gap: 4px; }.logo-copy strong { color: var(--text); font-size: 12px; font-weight: 650; }.logo-copy small, .upload-hint { color: var(--muted); font-size: 11px; }
.label-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 22px; }
.text-button { display: inline-flex; align-items: center; gap: 5px; padding: 2px 0; border: 0; background: transparent; color: var(--accent); font: inherit; font-size: 11px; cursor: pointer; }
.inline-client-form { display: grid; gap: 12px; padding: 14px; border: 1px solid var(--border); border-radius: 12px; background: var(--control); }
.verified-control { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 4px; color: var(--muted); font-size: 12px; cursor: pointer; }
.verified-control input { appearance: none; position: relative; width: 36px; height: 21px; margin: 0; flex-shrink: 0; border: 1px solid var(--border); border-radius: 99px; background: var(--control); cursor: pointer; }
.verified-control input::after { content: ""; position: absolute; top: 3px; left: 3px; width: 13px; height: 13px; border-radius: 50%; background: var(--muted); }
.verified-control input:checked { border-color: var(--accent); background: var(--accent); }
.verified-control input:checked::after { transform: translateX(15px); background: white; }
.verified-control input:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.form-error { grid-column: 1 / -1; margin: 0; padding: 12px 16px; border: 1px solid color-mix(in srgb, var(--danger) 25%, transparent); border-radius: 12px; background: var(--danger-soft); color: var(--danger); font-size: 13px; }
.club-form-actions { position: sticky; bottom: 12px; z-index: 5; grid-column: 1 / -1; display: flex; justify-content: flex-end; align-items: center; gap: 24px; padding: 14px 18px; border: 1px solid var(--panel-border); border-radius: 14px; background: color-mix(in srgb, var(--surface) 94%, transparent); backdrop-filter: blur(12px); }
.cancel-link { color: var(--muted); text-decoration: none; font-size: 13px; }.cancel-link:hover { color: var(--text); }
.save-button { min-width: 130px; min-height: 42px; border-radius: 10px; font-size: 13px; }
.back-link:focus-visible, .text-button:focus-visible, .service-chip button:focus-visible, .cancel-link:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
@media (max-width: 1100px) { .venue-form { grid-template-columns: minmax(0, 1fr) 250px; gap: 16px; }.form-card { padding: 20px; }.field-grid { gap: 12px; } }
@media (max-width: 900px) { .venue-form { grid-template-columns: 1fr; }.form-aside { grid-template-columns: repeat(2, minmax(0, 1fr)); }.form-card { padding: 20px; } }
@media (max-width: 600px) {
  .club-form-header { margin-bottom: 18px; gap: 10px; }.club-form-header h1 { font-size: 20px; }.back-link { width: 34px; height: 34px; }
  .venue-form, .form-main, .form-aside { gap: 14px; }.form-aside, .field-grid { grid-template-columns: 1fr; }.coordinates-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .form-card { padding: 18px; gap: 16px; border-radius: 14px; }.form-group input, .form-group select, .form-group textarea { font-size: 16px; }
  .club-form-actions { bottom: max(8px, env(safe-area-inset-bottom)); padding: 12px 14px; }.save-button { min-width: 140px; }.cover-upload { min-height: 120px; }
}
@media (prefers-reduced-motion: reduce) { .form-group input, .form-group select, .form-group textarea { transition: none; } }
</style>
