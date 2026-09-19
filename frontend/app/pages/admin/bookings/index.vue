<script setup lang="ts">
import { useAdminApi } from "~/api/admin"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

useHead({
  title: "Bronlar boshqaruvi",
})

const adminApi = useAdminApi()

const bookings = ref<any[]>([])
const clubs = ref<any[]>([])
const isLoading = ref(true)
const errorMessage = ref("")

const statusFilter = ref("")
const selectedClubId = ref("")
const selectedDate = ref("")
const searchQuery = ref("")
const totalCount = ref(0)

// Cancel modal
const showCancelModal = ref(false)
const cancelBookingId = ref("")
const cancelReason = ref("")
const isCancelling = ref(false)
const cancelError = ref("")

const statusTabs = [
  { value: "", label: "Barchasi" },
  { value: "CONFIRMED", label: "Tasdiqlangan" },
  { value: "CHECKED_IN", label: "O'ynayapti" },
  { value: "PENDING_CONFIRMATION", label: "Kutilmoqda" },
  { value: "COMPLETED", label: "Tugallangan" },
  { value: "CANCELLED", label: "Bekor qilingan" },
  { value: "NO_SHOW", label: "Kelmadi" },
]

const fetchClubs = async () => {
  try {
    const res = await adminApi.getClubs({ page_size: 100 })
    clubs.value = res.results || res.data || res || []
  } catch (err) {
    console.error("Failed to load clubs", err)
  }
}

const fetchBookings = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = { page_size: 50 }
    if (statusFilter.value) params.status = statusFilter.value
    if (selectedClubId.value) params.club_id = selectedClubId.value
    if (selectedDate.value) params.date = selectedDate.value
    if (searchQuery.value) params.query = searchQuery.value

    const res = await adminApi.getBookings(params)
    bookings.value = res.results || res.data || res || []
    totalCount.value = res.count || bookings.value.length
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const handleCheckIn = async (bId: string) => {
  try {
    await adminApi.checkInBooking(bId)
    await fetchBookings()
  } catch (err: any) {
    alert(err?.data?.message || err?.message || "Check-in xatolik yuz berdi")
  }
}

const handleComplete = async (bId: string) => {
  try {
    await adminApi.completeBooking(bId)
    await fetchBookings()
  } catch (err: any) {
    alert(err?.data?.message || err?.message || "Tugatishda xatolik yuz berdi")
  }
}

const handleNoShow = async (bId: string) => {
  if (!confirm("Foydalanuvchi kelmadi deb belgilamoqchimisiz?")) return
  try {
    await adminApi.noShowBooking(bId)
    await fetchBookings()
  } catch (err: any) {
    alert(err?.data?.message || err?.message || "Xatolik yuz berdi")
  }
}

const openCancelModal = (bId: string) => {
  cancelBookingId.value = bId
  cancelReason.value = ""
  cancelError.value = ""
  showCancelModal.value = true
}

const submitCancel = async () => {
  if (!cancelBookingId.value) return
  isCancelling.value = true
  cancelError.value = ""
  try {
    await adminApi.cancelBooking(cancelBookingId.value, cancelReason.value)
    showCancelModal.value = false
    await fetchBookings()
  } catch (err: any) {
    cancelError.value = err?.data?.message || err?.message || "Bekor qilishda xatolik yuz berdi"
  } finally {
    isCancelling.value = false
  }
}

const formatPrice = (tiyin: number) => {
  const sum = Math.round((tiyin || 0) / 100)
  return new Intl.NumberFormat("uz-UZ").format(sum) + " so'm"
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " (" + d.toLocaleDateString() + ")"
}

onMounted(() => {
  void fetchClubs()
  void fetchBookings()
})
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Bronlar boshqaruvi</h1>
        <p class="page-subtitle">Jonli bronlar, check-in va buyurtmalarni boshqarish</p>
      </div>
      <button type="button" class="primary-button" :disabled="isLoading" @click="fetchBookings">
        <span>🔄 Yangilash</span>
      </button>
    </div>

    <!-- Status Tabs -->
    <div class="status-tabs-nav">
      <button
        v-for="tab in statusTabs"
        :key="tab.value"
        type="button"
        class="tab-btn"
        :class="{ 'is-active': statusFilter === tab.value }"
        @click="statusFilter = tab.value; fetchBookings()"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="search-input-wrap">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Mijoz ismi, telefon yoki klub nomi..."
          @keyup.enter="fetchBookings"
        >
      </div>
      <div class="select-wrap">
        <select v-model="selectedClubId" @change="fetchBookings">
          <option value="">Barcha klublar</option>
          <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="date-wrap">
        <input v-model="selectedDate" type="date" @change="fetchBookings">
      </div>
      <button type="button" class="secondary-button" @click="fetchBookings">Qidirish</button>
    </div>

    <!-- Table -->
    <div v-if="isLoading" class="loading-box">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <div v-else-if="errorMessage" class="error-banner">
      <p>{{ errorMessage }}</p>
      <button type="button" class="secondary-button" @click="fetchBookings">Qayta urinish</button>
    </div>

    <div v-else class="table-card">
      <div v-if="!bookings.length" class="empty-state">
        Bronlar topilmadi.
      </div>

      <div v-else class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>ID / Mijoz</th>
              <th>Klub / Filial / Zona</th>
              <th>Boshlanish</th>
              <th>Tugash</th>
              <th>Miqdor</th>
              <th>Summa</th>
              <th>Holat</th>
              <th>Amallar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in bookings" :key="b.id">
              <td>
                <div class="customer-info">
                  <span class="booking-id">#{{ b.id.slice(0, 8) }}</span>
                  <span class="customer-name">{{ b.user?.full_name || b.user?.username || "Mijoz" }}</span>
                  <span class="customer-phone">{{ b.user?.phone || "—" }}</span>
                </div>
              </td>
              <td>
                <div class="location-info">
                  <span class="club-name">{{ b.zone?.branch?.club?.name || b.zone?.branch?.name }}</span>
                  <span class="zone-name">{{ b.zone?.name }}</span>
                </div>
              </td>
              <td>{{ formatDate(b.starts_at) }}</td>
              <td>{{ formatDate(b.ends_at) }}</td>
              <td>
                <span class="qty-badge">{{ b.quantity }} dona</span>
              </td>
              <td>
                <span class="price-val">{{ formatPrice(b.total_price_tiyin) }}</span>
              </td>
              <td>
                <span class="status-badge" :class="b.status.toLowerCase()">
                  {{ b.status }}
                </span>
              </td>
              <td>
                <div class="action-buttons-inline">
                  <button
                    v-if="b.status === 'CONFIRMED'"
                    type="button"
                    class="btn-act checkin"
                    title="Check-in qilish"
                    @click="handleCheckIn(b.id)"
                  >
                    Check-in
                  </button>
                  <button
                    v-if="b.status === 'CHECKED_IN'"
                    type="button"
                    class="btn-act complete"
                    title="Tugatish"
                    @click="handleComplete(b.id)"
                  >
                    Tugatish
                  </button>
                  <button
                    v-if="b.status === 'CONFIRMED'"
                    type="button"
                    class="btn-act noshow"
                    title="Kelmadi"
                    @click="handleNoShow(b.id)"
                  >
                    Kelmadi
                  </button>
                  <button
                    v-if="['CONFIRMED', 'PENDING_CONFIRMATION'].includes(b.status)"
                    type="button"
                    class="btn-act cancel"
                    title="Bekor qilish"
                    @click="openCancelModal(b.id)"
                  >
                    Bekor qilish
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Cancel Modal -->
    <Teleport to="body">
      <div v-if="showCancelModal" class="modal-backdrop" @click.self="showCancelModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>Bronni bekor qilish</h3>
            <button type="button" class="modal-close-btn" @click="showCancelModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="submitCancel">
            <p v-if="cancelError" class="form-error">{{ cancelError }}</p>
            <div class="form-group">
              <label>Bekor qilish sababi</label>
              <textarea v-model="cancelReason" rows="3" placeholder="Mijoz iltimosiga ko'ra yoki boshqa sabab..." />
            </div>
            <div class="modal-actions">
              <button type="button" class="secondary-button" @click="showCancelModal = false">Bekor qilish</button>
              <button type="submit" class="primary-button danger" :disabled="isCancelling">
                {{ isCancelling ? "Bekor qilinmoqda..." : "Bekor qilishni tasdiqlash" }}
              </button>
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

.status-tabs-nav {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.tab-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: var(--text);
  border-color: var(--accent);
}

.tab-btn.is-active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
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

.search-input-wrap {
  flex: 1;
  min-width: 240px;
}

.search-input-wrap input, .select-wrap select, .date-wrap input {
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
  padding: 12px 14px;
  color: var(--muted);
  font-weight: 600;
  border-bottom: 1px solid var(--panel-border);
  background: color-mix(in srgb, var(--surface) 90%, black);
}

.admin-table td {
  padding: 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
  vertical-align: middle;
}

.customer-info, .location-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.booking-id {
  font-family: monospace;
  font-size: 11px;
  color: var(--muted);
}

.customer-name, .club-name {
  font-weight: 600;
}

.customer-phone, .zone-name {
  font-size: 11px;
  color: var(--muted);
}

.qty-badge {
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--control);
  border: 1px solid var(--border);
  font-size: 11px;
}

.price-val {
  font-weight: 700;
  color: var(--accent);
}

.status-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.status-badge.confirmed { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-badge.checked_in { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.status-badge.completed { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }
.status-badge.cancelled { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.status-badge.pending_confirmation { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.status-badge.no_show { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

.action-buttons-inline {
  display: flex;
  gap: 6px;
}

.btn-act {
  padding: 4px 8px;
  border-radius: 6px;
  border: none;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.btn-act.checkin { background: #3b82f6; color: #fff; }
.btn-act.complete { background: #10b981; color: #fff; }
.btn-act.noshow { background: #f59e0b; color: #fff; }
.btn-act.cancel { background: #ef4444; color: #fff; }

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
  width: min(100%, 460px);
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 20px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
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
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.form-group textarea {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 13px;
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

.primary-button.danger {
  background: #ef4444;
}
</style>
