<script setup lang="ts">
import { useAdminApi } from "~/api/admin"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

const adminApi = useAdminApi()

const clubs = ref<any[]>([])
const branches = ref<any[]>([])
const cities = ref<any[]>([])
const districts = ref<any[]>([])
const selectedClubId = ref("")
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
  name: "",
  city: "",
  district: "",
  address: "",
  phone: "",
  latitude: 41.2995,
  longitude: 69.2401,
  status: "ACTIVE",
  is_24_hours: true,
})

// Zone Modal
const showZoneModal = ref(false)
const editingZone = ref<any>(null)
const isSavingZone = ref(false)
const zoneModalError = ref("")
const zoneForm = ref({
  branch: "",
  name: "",
  resource_type: "COMPUTER",
  booking_type: "PER_SEAT",
  capacity: 10,
  unit_count: 10,
  price_per_hour_tiyin: 2000000,
  status: "ACTIVE",
})

const fetchData = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const [clubsRes, citiesRes] = await Promise.all([
      adminApi.getClubs({ page_size: 100 }),
      adminApi.getCities(),
    ])
    clubs.value = clubsRes.results || clubsRes.data || clubsRes || []
    cities.value = citiesRes.results || citiesRes.data || citiesRes || []

    await fetchBranches()
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const fetchBranches = async () => {
  isLoading.value = true
  try {
    const params: Record<string, any> = { page_size: 100 }
    if (selectedClubId.value) params.club_id = selectedClubId.value

    const res = await adminApi.getBranches(params)
    branches.value = res.results || res.data || res || []
    if (branches.value.length > 0 && !selectedBranch.value) {
      void selectBranch(branches.value[0])
    }
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const selectBranch = async (branch: any) => {
  selectedBranch.value = branch
  isZonesLoading.value = true
  try {
    const res = await adminApi.getZones({ branch_id: branch.id })
    branchZones.value = res.results || res.data || res || []
  } catch (err) {
    console.error("Failed to load zones", err)
  } finally {
    isZonesLoading.value = false
  }
}

const onCityChange = async (cityId: string) => {
  if (!cityId) {
    districts.value = []
    return
  }
  try {
    const res = await adminApi.getDistricts(cityId)
    districts.value = res.results || res.data || res || []
  } catch (err) {
    console.error("Failed to fetch districts", err)
  }
}

const openCreateBranchModal = () => {
  editingBranch.value = null
  branchForm.value = {
    club: selectedClubId.value || (clubs.value[0]?.id || ""),
    name: "",
    city: cities.value[0]?.id || "",
    district: "",
    address: "",
    phone: "",
    latitude: 41.2995,
    longitude: 69.2401,
    status: "ACTIVE",
    is_24_hours: true,
  }
  if (branchForm.value.city) {
    void onCityChange(branchForm.value.city)
  }
  branchModalError.value = ""
  showBranchModal.value = true
}

const openEditBranchModal = (b: any) => {
  editingBranch.value = b
  branchForm.value = {
    club: b.club?.id || b.club || "",
    name: b.name,
    city: b.city?.id || b.city || "",
    district: b.district?.id || b.district || "",
    address: b.address,
    phone: b.phone || "",
    latitude: b.latitude || 41.2995,
    longitude: b.longitude || 69.2401,
    status: b.status || "ACTIVE",
    is_24_hours: b.is_24_hours ?? true,
  }
  if (branchForm.value.city) {
    void onCityChange(branchForm.value.city)
  }
  branchModalError.value = ""
  showBranchModal.value = true
}

const saveBranch = async () => {
  if (!branchForm.value.name.trim() || !branchForm.value.address.trim()) {
    branchModalError.value = "Filial nomi va manzilini kiriting"
    return
  }
  isSavingBranch.value = true
  branchModalError.value = ""
  try {
    if (editingBranch.value) {
      await adminApi.updateBranch(editingBranch.value.id, branchForm.value)
    } else {
      await adminApi.createBranch(branchForm.value)
    }
    showBranchModal.value = false
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
    resource_type: "COMPUTER",
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
    resource_type: z.resource_type || "COMPUTER",
    booking_type: z.booking_type || "PER_SEAT",
    capacity: z.capacity || 10,
    unit_count: z.unit_count || 10,
    price_per_hour_tiyin: z.price_per_hour_tiyin || 2000000,
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
      await adminApi.updateZone(editingZone.value.id, zoneForm.value)
    } else {
      await adminApi.createZone(zoneForm.value)
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
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Filiallar va Zonalar</h1>
        <p class="page-subtitle">Filiallar va ularning o'yin zonalari (kompyuterlar, konsollar, narxlar)</p>
      </div>
      <div class="header-actions">
        <button type="button" class="primary-button" @click="openCreateBranchModal">
          <span>🏢 Yangi filial qo'shish</span>
        </button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="club-filter-select">
        <label>Klubni tanlang:</label>
        <select v-model="selectedClubId" @change="fetchBranches">
          <option value="">Barcha klublar filiallari</option>
          <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
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
              <span class="status-badge" :class="b.status.toLowerCase()">{{ b.status }}</span>
            </div>
            <p class="bic-address">📍 {{ b.address }}</p>
            <div class="bic-footer">
              <span class="bic-phone">📞 {{ b.phone || "—" }}</span>
              <div class="bic-actions" @click.stop>
                <button type="button" class="action-btn" title="Tahrirlash" @click="openEditBranchModal(b)">✏️</button>
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
            <button type="button" class="primary-button add-zone-btn" @click="openCreateZoneModal">
              <span>➕ Zona qo'shish</span>
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
                <span class="zmc-type-icon">{{ z.resource_type === 'COMPUTER' ? '🖥️' : '🎮' }}</span>
                <span class="status-badge" :class="z.status.toLowerCase()">{{ z.status }}</span>
              </div>
              <h4 class="zmc-title">{{ z.name }}</h4>
              <div class="zmc-specs">
                <span class="spec-tag">👥 Sig'im: {{ z.capacity }} kishi</span>
                <span class="spec-tag">🕹️ Joylar: {{ z.unit_count }} dona</span>
                <span class="spec-tag">{{ z.booking_type === 'PER_SEAT' ? 'Har bir joy' : 'Butun xona' }}</span>
              </div>
              <div class="zmc-price">
                {{ formatPrice(z.price_per_hour_tiyin) }}
              </div>
              <div class="zmc-footer">
                <button type="button" class="action-btn" @click="openEditZoneModal(z)">✏️ Tahrirlash</button>
                <button type="button" class="action-btn delete" @click="deleteZone(z)">🗑️ O'chirish</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Branch Modal -->
    <Teleport to="body">
      <div v-if="showBranchModal" class="modal-backdrop" @click.self="showBranchModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>{{ editingBranch ? 'Filialni tahrirlash' : 'Yangi filial qo‘shish' }}</h3>
            <button type="button" class="modal-close-btn" @click="showBranchModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="saveBranch">
            <p v-if="branchModalError" class="form-error">{{ branchModalError }}</p>

            <div class="form-group">
              <label>Klub *</label>
              <select v-model="branchForm.club" required>
                <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>

            <div class="form-group">
              <label>Filial nomi *</label>
              <input v-model="branchForm.name" type="text" placeholder="Masalan: Chilonzor filiali" required>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Shahar *</label>
                <select v-model="branchForm.city" @change="onCityChange(branchForm.city)">
                  <option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option>
                </select>
              </div>
              <div class="form-group">
                <label>Tuman</label>
                <select v-model="branchForm.district">
                  <option value="">Tanlanmagan</option>
                  <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>Manzil *</label>
              <input v-model="branchForm.address" type="text" placeholder="Ko'cha va uy raqami" required>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Telefon</label>
                <input v-model="branchForm.phone" type="tel" placeholder="+998 90 123 45 67">
              </div>
              <div class="form-group">
                <label>Holat</label>
                <select v-model="branchForm.status">
                  <option value="ACTIVE">ACTIVE (Faol)</option>
                  <option value="INACTIVE">INACTIVE (Nofaol)</option>
                  <option value="MAINTENANCE">MAINTENANCE (Ta'mirlash)</option>
                </select>
              </div>
            </div>

            <div class="form-checkbox">
              <label>
                <input v-model="branchForm.is_24_hours" type="checkbox">
                <span>24/7 rejimida ishlaydi</span>
              </label>
            </div>

            <div class="modal-actions">
              <button type="button" class="secondary-button" @click="showBranchModal = false">Bekor qilish</button>
              <button type="submit" class="primary-button" :disabled="isSavingBranch">{{ isSavingBranch ? "Saqlanmoqda..." : "Saqlash" }}</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Zone Modal -->
    <Teleport to="body">
      <div v-if="showZoneModal" class="modal-backdrop" @click.self="showZoneModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>{{ editingZone ? 'Zonani tahrirlash' : 'Yangi zona qo‘shish' }}</h3>
            <button type="button" class="modal-close-btn" @click="showZoneModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="saveZone">
            <p v-if="zoneModalError" class="form-error">{{ zoneModalError }}</p>

            <div class="form-group">
              <label>Zona nomi *</label>
              <input v-model="zoneForm.name" type="text" placeholder="Masalan: VIP PC Zal, PS5 Room" required>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Qurilma turi</label>
                <select v-model="zoneForm.resource_type">
                  <option value="COMPUTER">🖥️ Computer (Kompyuter)</option>
                  <option value="PLAYSTATION">🎮 PlayStation</option>
                </select>
              </div>
              <div class="form-group">
                <label>Bronlash turi</label>
                <select v-model="zoneForm.booking_type">
                  <option value="PER_SEAT">Har bir joy uchun</option>
                  <option value="PER_ZONE">Butun xona uchun</option>
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
              <input v-model.number="zoneForm.price_per_hour_tiyin" type="number" min="0" step="100000" required>
            </div>

            <div class="form-group">
              <label>Holat</label>
              <select v-model="zoneForm.status">
                <option value="ACTIVE">ACTIVE (Faol)</option>
                <option value="MAINTENANCE">MAINTENANCE (Ta'mirda)</option>
                <option value="DISABLED">DISABLED (O'chirilgan)</option>
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
