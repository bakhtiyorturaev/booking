<script setup lang="ts">
import VenueBillingBadge from "~/components/cabinet/VenueBillingBadge.vue"
import { useAdminApi } from "~/api/admin"
import { useAuth } from "~/composables/useAuth"

definePageMeta({
  alias: ["/site/staff/panel/clubs", "/site/client/panel/clubs"],
  layout: "admin",
  middleware: ["admin"],
})

useHead({
  title: "Muassasalar",
})

const cabinetPath = useCabinetPath()
const { user: currentUser } = useAuth()
const adminApi = useAdminApi()
const route = useRoute()
const categoryLabels: Record<string, string> = { GAMING_CLUB: "O‘yin klubi", BARBERSHOP: "Sartaroshxona", BILLIARDS: "Bilyard", OTHER: "Boshqa xizmat" }
const { statusLabel } = useCabinetLabels()

const isPlatformAdmin = computed(() => {
  const role = currentUser.value?.role
  return role === "ADMIN" || role === "MODERATOR" || currentUser.value?.is_staff || currentUser.value?.is_superuser
})

const services = ref<{ id: string; code: string; name: string }[]>([])
const cities = ref<any[]>([])
const loadLocations = async () => {
  try { cities.value = await adminApi.getCities() } catch (error) { errorMessage.value = cabinetErrorMessage(error) }
}
const clubs = ref<any[]>([])
const billingStatuses = useCabinetBillingCache()
const clientsList = ref<any[]>([])
const isLoading = ref(true)
const searchQuery = ref("")
const selectedStatus = ref("")
const selectedCategory = ref("")
const totalCount = ref(0)
const errorMessage = ref("")

// Modal state
const page = ref(1)
const hasNextPage = ref(false)
watch([searchQuery, selectedStatus, selectedCategory], () => { page.value = 1 }, { flush: "sync" })
const showModal = ref(false)
const showNewClient = ref(false)
const creatingClient = ref(false)
const newClient = ref({ full_name: "", phone: "", username: "", password: "" })
const createClientHere = async () => {
  if (creatingClient.value) return
  creatingClient.value = true; modalError.value = ""
  try {
    const client = await adminApi.createUser({ ...newClient.value })
    clientsList.value.push(client)
    form.value.owner = client.id
    showNewClient.value = false
    newClient.value = { full_name: "", phone: "", username: "", password: "" }
  } catch (error) { modalError.value = cabinetErrorMessage(error) }
  finally { creatingClient.value = false }
}
watch(showModal, visible => { if (!visible) { showNewClient.value = false; newClient.value.password = "" } })
const editingClub = ref<any>(null)
const isSaving = ref(false)
const modalError = ref("")

const form = ref({
  name: "",
  owner: null as string | null,
  category: "GAMING_CLUB",
  service_type: "", billing_city: "", billing_district: "",
  service_name: "",
  description: "",
  phone: "",
  email: "",
  website: "",
  status: "ACTIVE",
  is_verified: true,
})

const { districts, isDistrictLoading, districtError } = useCityDistricts(() => form.value.billing_city)

const fetchClubs = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = { page: page.value }
    if (searchQuery.value) params.query = searchQuery.value
    if (selectedStatus.value) params.status = selectedStatus.value
    if (selectedCategory.value) params.service_type = selectedCategory.value

    const res = await adminApi.getClubs(params)
    clubs.value = res.results || res.data || res || []
    if (!isPlatformAdmin.value) {
      billingStatuses.value = { ...billingStatuses.value, ...Object.fromEntries(clubs.value.filter(club => club.billing).map(club => [club.id, club.billing])) }
    }
    totalCount.value = res.count || clubs.value.length
    hasNextPage.value = Boolean(res.next)
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const fetchClients = async () => {
  if (!isPlatformAdmin.value) return
  try {
    let clientPage = 1
    const clients: any[] = []
    let next = true
    while (next) {
      const res = await adminApi.getUsers({ role: "CLIENT", status: "ACTIVE", page_size: 100, page: clientPage++ })
      clients.push(...res.results)
      next = Boolean(res.next)
    }
    clientsList.value = clients
  } catch (err) {
    console.error("Failed to fetch clients", err)
  }
}

const openCreateModal = () => {
  showNewClient.value = false
  editingClub.value = null
  form.value = {
    name: "",
    owner: null,
    category: "GAMING_CLUB",
  service_type: "", billing_city: "", billing_district: "",
    service_name: "",
    description: "",
    phone: "",
    email: "",
    website: "",
    status: isPlatformAdmin.value ? "ACTIVE" : "DRAFT",
    is_verified: Boolean(isPlatformAdmin.value),
  }
  modalError.value = ""
  showModal.value = true
}

const openEditModal = (club: any) => {
  showNewClient.value = false
  editingClub.value = club
  form.value = {
    name: club.name,
    owner: club.owner || club.owner_details?.id || null,
    category: club.category || "GAMING_CLUB",
    service_type: club.service_type || "", billing_city: club.billing_city || "", billing_district: club.billing_district || "",
    service_name: club.service_name || "",
    description: club.description || "",
    phone: club.phone || "",
    email: club.email || "",
    website: club.website || "",
    status: club.status || "ACTIVE",
    is_verified: club.is_verified || false,
  }
  modalError.value = ""
  showModal.value = true
}

const saveClub = async () => {
  if (isSaving.value) return
  if (!form.value.name.trim()) {
    modalError.value = "Muassasa nomini kiriting"
    return
  }

  isSaving.value = true
  modalError.value = ""

  try {
    const { owner, ...rest } = form.value
    const payload = { ...rest, service_type: rest.service_type || null, billing_city: rest.billing_city || null, billing_district: rest.billing_district || null, ...(isPlatformAdmin.value && owner ? { owner } : {}) }
    if (editingClub.value) {
      await adminApi.updateClub(editingClub.value.id, payload)
    } else {
      await adminApi.createClub(payload)
    }
    showModal.value = false
    await fetchClubs()
  } catch (err: any) {
    modalError.value = cabinetErrorMessage(err)
  } finally {
    isSaving.value = false
  }
}

const toggleClubStatus = async (club: any) => {
  const nextStatus = club.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE"
  try {
    await adminApi.updateClub(club.id, { status: nextStatus })
    await fetchClubs()
  } catch (err) {
    console.error("Failed to toggle status", err)
  }
}

const deleteClub = async (club: any) => {
  if (!confirm(`"${club.name}" klubini arxivlamoqchimisiz?`)) return
  try {
    await adminApi.deleteClub(club.id)
    await fetchClubs()
  } catch (err) {
    console.error("Failed to delete club", err)
  }
}

onMounted(async () => {
  try { services.value = await adminApi.getServiceTypes(); await loadLocations() } catch (error) { errorMessage.value = cabinetErrorMessage(error) }
  if (typeof route.query.query === "string") searchQuery.value = route.query.query
  await Promise.all([fetchClubs(), fetchClients()])
  if (isPlatformAdmin.value && typeof route.query.owner === "string") {
    openCreateModal(); form.value.owner = route.query.owner
  }
})
useDialogFocus(showModal, "#cabinet-clubs-showModal", () => { showModal.value = false })
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Muassasalar</h1>
      </div>
      <button type="button" class="primary-button create-btn" @click="openCreateModal">
        <span><CabinetIcon name="plus" /> Muassasa qo‘shish</span>
      </button>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Muassasa nomi yoki telefon bo'yicha qidirish..."
          @keyup.enter="fetchClubs"
         aria-label="Muassasa nomi yoki telefon bo'yicha qidirish...">
      </div>
      <div class="select-box">
        <select v-model="selectedCategory" @change="fetchClubs" aria-label="Xizmat turi"><option value="">Barcha xizmatlar</option><option v-for="service in services" :key="service.id" :value="service.id">{{ service.name }}</option></select>
      </div>
      <div class="select-box">
        <select v-model="selectedStatus" @change="fetchClubs" aria-label="Holat">
          <option value="">Barcha holatlar</option>
          <option value="ACTIVE">Faol</option>
          <option value="DRAFT">DRAFT (Qoralama)</option>
          <option value="PENDING">Kutilmoqda</option>
          <option value="SUSPENDED">SUSPENDED (Muzlatilgan)</option>
          <option value="ARCHIVED">ARCHIVED (Arxivlangan)</option>
        </select>
      </div>
      <button type="button" class="secondary-button" @click="fetchClubs">
        Qidirish
      </button>
    </div>

    <!-- Table content -->
    <div v-if="isLoading" class="loading-box">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <div v-else-if="errorMessage" class="error-banner">
      <p>{{ errorMessage }}</p>
      <button type="button" class="secondary-button" @click="fetchClubs">
        Qayta urinish
      </button>
    </div>

    <div v-else class="table-card">
      <div v-if="!clubs.length" class="empty-state">
        Muassasalar topilmadi.
      </div>
      <div v-else class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th scope="col">Nomi</th>
              <th scope="col" v-if="isPlatformAdmin">Egasi</th>
              <th scope="col">Toifa</th>
              <th scope="col">Slug (URL)</th>
              <th scope="col">Telefon</th>
              <th scope="col">To‘lov muddati</th>
              <th scope="col">Holat</th>
              <th scope="col">Tekshiruv</th>
              <th scope="col">Reyting</th>
              <th scope="col">Amallar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in clubs" :key="c.id">
              <td data-label="Nomi">
                <div class="club-info">
                  <div class="club-avatar">{{ c.name.slice(0, 1).toUpperCase() }}</div>
                  <div>
                    <span class="club-title">{{ c.name }}</span>
                    <span v-if="c.email" class="club-sub">{{ c.email }}</span>
                  </div>
                </div>
              </td>
              <td data-label="Egasi" v-if="isPlatformAdmin">
                <span v-if="c.owner_details">
                  <strong>{{ c.owner_details.full_name || c.owner_details.username }}</strong>
                  <small style="display: block; color: var(--muted); font-size: 11px;">@{{ c.owner_details.username }}</small>
                </span>
                <span v-else style="color: var(--muted);">—</span>
              </td>
              <td data-label="Toifa">
                <span class="category-pill" :class="c.category === 'BARBERSHOP' ? 'barbershop' : 'gaming'">
                  {{ c.service_type_name || c.service_name || categoryLabels[c.category] }}
                </span>
              </td>
              <td data-label="Slug (URL)"><code>{{ c.slug }}</code></td>
              <td data-label="Telefon">{{ c.phone || "—" }}</td>
              <td data-label="To‘lov muddati"><VenueBillingBadge v-if="c.billing" :billing="c.billing" :club-id="c.id" /><span v-else>—</span></td>
              <td data-label="Holat">
                <span class="status-badge" :class="c.status.toLowerCase()">
                  {{ statusLabel(c.status) }}
                </span>
              </td>
              <td data-label="Tekshiruv">
                <span class="verified-badge" :class="{ 'is-v': c.is_verified }">
                  {{ c.is_verified ? 'Tasdiqlangan' : 'Tasdiqlanmagan' }}
                </span>
              </td>
              <td data-label="Reyting"><CabinetIcon name="star" /> {{ Number(c.rating || 0).toFixed(1) }} ({{ c.review_count || 0 }})</td>
              <td data-label="Amallar">
                <div class="table-actions">
                  <button
                    type="button"
                    class="action-btn edit"
                    title="Tahrirlash"
                    @click="openEditModal(c)"
                  >
                    <CabinetIcon name="edit" />
                  </button>
                  <button
                    type="button"
                    class="action-btn delete"
                    title="O'chirish"
                    @click="deleteClub(c)"
                  >
                    <CabinetIcon name="delete" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="totalCount > 20" class="cabinet-pagination"><span>{{ page }}-sahifa · {{ totalCount }} ta</span><div><button type="button" class="secondary-button" :disabled="page === 1 || isLoading" @click="page--; fetchClubs()">Oldingi</button><button type="button" class="secondary-button" :disabled="!hasNextPage || isLoading" @click="page++; fetchClubs()">Keyingi</button></div></div>
    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div v-if="showModal" id="cabinet-clubs-showModal" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" aria-label="Tahrirlash" tabindex="-1" @click.self="showModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>{{ editingClub ? "Muassasani tahrirlash" : "Yangi muassasa qo'shish" }}</h3>
            <button type="button" class="modal-close-btn" @click="showModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="saveClub">
            <p v-if="modalError" class="form-error">{{ modalError }}</p>

            <div class="form-row">
              <div class="form-group">
                <label>Nomi *</label>
                <input v-model="form.name" type="text" placeholder="Muassasa nomi" required aria-label="Muassasa nomi">
              </div>
              <div class="form-group">
                <label for="club-service-type">Xizmat turi *</label>
                <select id="club-service-type" v-model="form.service_type" :disabled="!isPlatformAdmin && Boolean(editingClub)" required aria-label="Xizmat turi"><option value="" disabled>Xizmatni tanlang</option><option v-for="service in services" :key="service.id" :value="service.id">{{ service.name }}</option></select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group"><label for="billing-city">Shahar</label><select id="billing-city" v-model="form.billing_city" required :disabled="!isPlatformAdmin && Boolean(editingClub)" @change="form.billing_district = ''"><option value="" disabled>Shaharni tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option></select></div>
              <div class="form-group"><label for="billing-district">Tuman</label><select id="billing-district" v-model="form.billing_district" :disabled="isDistrictLoading || !form.billing_city || (!isPlatformAdmin && Boolean(editingClub))" required><option value="" disabled>{{ isDistrictLoading ? "Yuklanmoqda…" : "Tumanni tanlang" }}</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option></select><small v-if="districtError" role="alert">{{ districtError }}</small><small v-else-if="form.billing_city && !isDistrictLoading && !districts.length">Bu hudud uchun tumanlar hali qo‘shilmagan.</small></div>
            </div>
            <div v-if="isPlatformAdmin" class="form-group">
              <label>Muassasa egasi</label><button type="button" class="secondary-button" @click="showNewClient = !showNewClient">Mijoz qo‘shish</button>
              <div v-if="showNewClient" class="inline-client-form">
                <label for="new-owner-name">Ism-familiya</label><input id="new-owner-name" v-model="newClient.full_name" maxlength="150" autocomplete="name">
                <label for="new-owner-phone">Telefon</label><input id="new-owner-phone" v-model="newClient.phone" type="tel" autocomplete="tel">
                <label for="new-owner-login">Login</label><input id="new-owner-login" v-model="newClient.username" maxlength="30" autocomplete="off" autocapitalize="none">
                <label for="new-owner-password">Parol</label><input id="new-owner-password" v-model="newClient.password" type="password" maxlength="128" autocomplete="new-password">
                <button type="button" class="primary-button" :disabled="creatingClient" @click="createClientHere">{{ creatingClient ? 'Saqlanmoqda…' : 'Mijozni saqlash' }}</button>
              </div>
              <select v-model="form.owner" aria-label="Tanlash">
                <option :value="null">O'zim (Platforma administratori)</option>
                <option v-for="cl in clientsList" :key="cl.id" :value="cl.id">
                  {{ cl.profile?.full_name || cl.username }} (@{{ cl.username }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Tavsif</label>
              <textarea v-model="form.description" rows="3" placeholder="Muassasa haqida" />
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Telefon</label>
                <input v-model="form.phone" type="tel" placeholder="+998 90 123 45 67">
              </div>
              <div class="form-group">
                <label>Email</label>
                <input v-model="form.email" type="email" placeholder="info@club.uz">
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Vebsayt</label>
                <input v-model="form.website" type="url" placeholder="https://club.uz">
              </div>
              <div class="form-group">
                <label>Holat</label>
                <select v-model="form.status" aria-label="Tanlash">
                  <option value="ACTIVE">Faol</option>
                  <option value="DRAFT">DRAFT (Qoralama)</option>
                  <option value="PENDING">Kutilmoqda</option>
                  <option value="SUSPENDED">SUSPENDED (Muzlatilgan)</option>
                </select>
              </div>
            </div>

            <div class="form-checkbox">
              <label>
                <input v-model="form.is_verified" type="checkbox">
                <span>Tekshiruvdan o'tgan deb belgilash (Verified badge)</span>
              </label>
            </div>

            <div class="modal-actions">
              <button type="button" class="secondary-button" @click="showModal = false">
                Bekor qilish
              </button>
              <button type="submit" class="primary-button" :disabled="isSaving || creatingClient || isDistrictLoading">
                {{ isSaving ? "Saqlanmoqda..." : "Saqlash" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.inline-client-form { display: grid; gap: 8px; padding: 16px; border: 1px solid var(--panel-border); border-radius: 10px; margin: 10px 0; }
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

.create-btn {
  padding: 8px 18px;
  font-size: 13px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
}

.search-box {
  flex: 1;
  min-width: 240px;
}

.search-box input, .select-box select {
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 13px;
}

.table-card {
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  overflow: hidden;
}

.table-container {
  overflow-x: auto;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}

.admin-table th {
  padding: 12px 16px;
  color: var(--muted);
  font-weight: 600;
  border-bottom: 1px solid var(--panel-border);
  background: color-mix(in srgb, var(--surface) 90%, black);
}

.admin-table td {
  padding: 14px 16px;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
  vertical-align: middle;
}

.club-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.club-avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--accent) 0%, #0088cc 100%);
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 14px;
}

.club-title {
  font-weight: 600;
  display: block;
}

.club-sub {
  font-size: 11px;
  color: var(--muted);
}

.category-pill {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  display: inline-block;
}

.category-pill.gaming {
  background: rgba(99, 102, 241, 0.15);
  color: #6366f1;
}

.category-pill.barbershop {
  background: rgba(245, 158, 11, 0.15);
  color: #d97706;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
}

.status-badge.active { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-badge.draft { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }
.status-badge.pending { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.status-badge.suspended { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.status-badge.archived { background: rgba(107, 114, 128, 0.15); color: #6b7280; }

.verified-badge {
  font-size: 12px;
  color: var(--muted);
}

.verified-badge.is-v {
  color: #10b981;
  font-weight: 600;
}

.rating-text {
  font-weight: 600;
}

.table-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--control);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s ease;
}

.action-btn:hover {
  border-color: var(--accent);
}

.empty-state {
  padding: 40px;
  text-align: center;
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

/* Modal */
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
  width: min(100%, 540px);
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

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}
</style>
