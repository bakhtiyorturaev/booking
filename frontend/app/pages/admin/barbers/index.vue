<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
import type { CabinetBarberItem } from "~/types/barber"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

const adminApi = useAdminApi()

const barbers = ref<CabinetBarberItem[]>([])
const isLoading = ref(true)
const searchQuery = ref("")
const selectedAffiliation = ref("")
const selectedRealtimeStatus = ref("")
const errorMessage = ref("")
const successMessage = ref("")

const fetchBarbers = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = {}
    if (searchQuery.value) params.search = searchQuery.value
    if (selectedAffiliation.value) params.affiliation_status = selectedAffiliation.value
    if (selectedRealtimeStatus.value) params.status = selectedRealtimeStatus.value

    const res = await adminApi.getBarbers(params)
    barbers.value = res.results || res.data || res || []
  } catch (err: any) {
    errorMessage.value = err?.message || "Sartaroshlarni yuklashda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const approveAffiliation = async (barber: CabinetBarberItem) => {
  try {
    await adminApi.approveBarberAffiliation(barber.id)
    const msg = `${barber.full_name} sartaroshxonaga muvaffaqiyatli biriktirildi!`
    successMessage.value = msg
    useToast().success(msg)
    setTimeout(() => { successMessage.value = "" }, 4000)
    await fetchBarbers()
  } catch (err: any) {
    const errText = err?.message || "Tasdiqlashda xatolik yuz berdi"
    errorMessage.value = errText
    useToast().error(errText)
  }
}

const rejectAffiliation = async (barber: CabinetBarberItem) => {
  if (!confirm(`${barber.full_name}ning birikish so'rovini rad etmoqchimisiz?`)) return
  try {
    await adminApi.rejectBarberAffiliation(barber.id)
    const msg = `${barber.full_name}ning so'rovi rad etildi.`
    successMessage.value = msg
    useToast().success(msg)
    setTimeout(() => { successMessage.value = "" }, 4000)
    await fetchBarbers()
  } catch (err: any) {
    const errText = err?.message || "Rad etishda xatolik yuz berdi"
    errorMessage.value = errText
    useToast().error(errText)
  }
}

const toggleActive = async (barber: CabinetBarberItem) => {
  try {
    await adminApi.toggleBarberStatus(barber.id)
    useToast().success("Holat muvaffaqiyatli o'zgartirildi")
    await fetchBarbers()
  } catch (err: any) {
    const errText = err?.message || "Holatni o'zgartirishda xatolik yuz berdi"
    errorMessage.value = errText
    useToast().error(errText)
  }
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case "AVAILABLE": return "badge-success"
    case "BREAK": return "badge-warning"
    case "NOT_AT_WORK": return "badge-orange"
    case "DAY_OFF": return "badge-danger"
    default: return "badge-secondary"
  }
}

const getAffiliationBadgeClass = (status: string) => {
  switch (status) {
    case "APPROVED": return "badge-success"
    case "PENDING": return "badge-warning"
    case "REJECTED": return "badge-danger"
    default: return "badge-secondary"
  }
}

onMounted(() => {
  fetchBarbers()
})
</script>

<template>
  <div class="admin-barbers-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">💈 Sartaroshlar Boshqaruvi</h1>
        <p class="page-subtitle">Platformadagi barcha sartaroshlar, real-vaqt holatlari va salonlarga birikish so'rovlari</p>
      </div>
      <div class="header-right">
        <button class="btn btn-outline" @click="fetchBarbers">
          🔄 Yangilash
        </button>
      </div>
    </div>

    <!-- Feedback Alerts -->
    <div v-if="successMessage" class="alert alert-success">
      <span>✓ {{ successMessage }}</span>
    </div>
    <div v-if="errorMessage" class="alert alert-error">
      <span>⚠️ {{ errorMessage }}</span>
    </div>

    <!-- Filters Bar -->
    <div class="filters-card">
      <div class="search-input-box">
        <span class="search-icon">🔍</span>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Ism, telefon yoki sartaroshxona nomi bo'yicha..."
          class="search-input"
          @keyup.enter="fetchBarbers"
        >
      </div>

      <div class="filter-selects">
        <select v-model="selectedAffiliation" class="filter-select" @change="fetchBarbers">
          <option value="">Barcha birikish holatlari</option>
          <option value="PENDING">⏳ Kutilmoqda (Moderatsiya)</option>
          <option value="APPROVED">✅ Tasdiqlangan</option>
          <option value="REJECTED">❌ Rad etilgan</option>
          <option value="NONE">Birikmagan</option>
        </select>

        <select v-model="selectedRealtimeStatus" class="filter-select" @change="fetchBarbers">
          <option value="">Barcha ish holatlari</option>
          <option value="AVAILABLE">🟢 Ishda</option>
          <option value="BREAK">🟡 Tanaffusda</option>
          <option value="NOT_AT_WORK">🟠 Hozircha ishda emas</option>
          <option value="DAY_OFF">🔴 Dam olish kuni</option>
        </select>
      </div>
    </div>

    <!-- Barbers Table -->
    <div class="table-container">
      <div v-if="isLoading" class="loading-state">
        <div class="spinner" />
        <p>Sartaroshlar yuklanmoqda...</p>
      </div>

      <div v-else-if="barbers.length === 0" class="empty-state">
        <div class="empty-icon">💈</div>
        <h3>Sartaroshlar topilmadi</h3>
        <p>Qidiruv shartlarini o'zgartirib ko'ring yoki yangilang.</p>
      </div>

      <table v-else class="data-table">
        <thead>
          <tr>
            <th>Usta</th>
            <th>Sartaroshxona / Filial</th>
            <th>Ish vaqti</th>
            <th>Ish holati</th>
            <th>Birikish</th>
            <th>Reyting</th>
            <th>Platforma holati</th>
            <th class="text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="barber in barbers" :key="barber.id">
            <!-- Master info -->
            <td>
              <div class="barber-user-info">
                <img
                  v-if="barber.photo"
                  :src="barber.photo"
                  :alt="barber.full_name"
                  class="barber-avatar"
                >
                <div v-else class="barber-avatar-placeholder">
                  {{ barber.full_name.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <div class="barber-name">{{ barber.full_name }}</div>
                  <div class="barber-phone">{{ barber.phone || barber.user_phone }}</div>
                </div>
              </div>
            </td>

            <!-- Barbershop / Branch -->
            <td>
              <div v-if="barber.club_name">
                <div class="club-title">💈 {{ barber.club_name }}</div>
                <div class="branch-sub">{{ barber.branch_name || 'Asosiy filial' }}</div>
              </div>
              <span v-else class="text-muted">Biriktirilmagan</span>
            </td>

            <!-- Working hours -->
            <td>
              <span class="hours-badge">
                {{ (barber.work_start_time || '09:00').slice(0, 5) }} - {{ (barber.work_end_time || '20:00').slice(0, 5) }}
              </span>
            </td>

            <!-- Real-time status -->
            <td>
              <span class="badge" :class="getStatusBadgeClass(barber.status)">
                {{ barber.status_display || barber.status }}
              </span>
            </td>

            <!-- Affiliation status -->
            <td>
              <span class="badge" :class="getAffiliationBadgeClass(barber.affiliation_status)">
                {{ barber.affiliation_status_display || barber.affiliation_status }}
              </span>
            </td>

            <!-- Rating -->
            <td>
              <div class="rating-box">
                ⭐ <strong>{{ Number(barber.rating).toFixed(1) }}</strong>
                <span class="reviews-num">({{ barber.review_count }})</span>
              </div>
            </td>

            <!-- Active / Inactive -->
            <td>
              <button
                type="button"
                class="status-toggle-btn"
                :class="barber.is_active ? 'active' : 'inactive'"
                @click="toggleActive(barber)"
              >
                {{ barber.is_active ? 'Faol' : 'Nofaol' }}
              </button>
            </td>

            <!-- Actions -->
            <td class="text-right">
              <div class="actions-group">
                <template v-if="barber.affiliation_status === 'PENDING'">
                  <button
                    class="btn-sm btn-success"
                    title="Birikishni tasdiqlash"
                    @click="approveAffiliation(barber)"
                  >
                    ✓ Tasdiqlash
                  </button>
                  <button
                    class="btn-sm btn-danger"
                    title="Birikishni rad etish"
                    @click="rejectAffiliation(barber)"
                  >
                    ✕ Rad
                  </button>
                </template>
                <button
                  v-else
                  class="btn-sm btn-outline"
                  @click="toggleActive(barber)"
                >
                  {{ barber.is_active ? 'Bloklash' : 'Faollashtirish' }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.admin-barbers-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-text, #0f172a);
}

.page-subtitle {
  font-size: 0.875rem;
  color: var(--color-text-muted, #64748b);
  margin: 0.25rem 0 0;
}

.filters-card {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 1rem;
  background: var(--color-bg-surface, #ffffff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 0.75rem;
}

.search-input-box {
  flex: 1;
  min-width: 260px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  font-size: 0.9rem;
  opacity: 0.6;
}

.search-input {
  width: 100%;
  padding: 0.6rem 0.75rem 0.6rem 2.25rem;
  border: 1px solid var(--color-border, #cbd5e1);
  border-radius: 0.5rem;
  background: var(--color-bg-input, #f8fafc);
  color: var(--color-text, #0f172a);
  font-size: 0.875rem;
}

.filter-selects {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filter-select {
  padding: 0.6rem 1rem;
  border: 1px solid var(--color-border, #cbd5e1);
  border-radius: 0.5rem;
  background: var(--color-bg-input, #f8fafc);
  color: var(--color-text, #0f172a);
  font-size: 0.875rem;
}

.table-container {
  background: var(--color-bg-surface, #ffffff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 0.75rem;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.875rem;
}

.data-table th {
  padding: 0.875rem 1rem;
  background: var(--color-bg-table-head, #f8fafc);
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.data-table td {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border, #f1f5f9);
  vertical-align: middle;
}

.barber-user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.barber-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
}

.barber-avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #6366f1;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.barber-name {
  font-weight: 600;
  color: var(--color-text, #0f172a);
}

.barber-phone {
  font-size: 0.8rem;
  color: var(--color-text-muted, #64748b);
}

.club-title {
  font-weight: 600;
  color: var(--color-text, #0f172a);
}

.branch-sub {
  font-size: 0.75rem;
  color: var(--color-text-muted, #64748b);
}

.hours-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  background: var(--color-bg-input, #f1f5f9);
  border-radius: 0.375rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-success { background: #dcfce7; color: #15803d; }
.badge-warning { background: #fef9c3; color: #a16207; }
.badge-orange { background: #ffedd5; color: #c2410c; }
.badge-danger { background: #fee2e2; color: #b91c1c; }
.badge-secondary { background: #f1f5f9; color: #475569; }

.status-toggle-btn {
  padding: 0.25rem 0.6rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.status-toggle-btn.active {
  background: #dcfce7;
  color: #166534;
}

.status-toggle-btn.inactive {
  background: #fee2e2;
  color: #991b1b;
}

.actions-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-sm {
  padding: 0.35rem 0.7rem;
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn-success { background: #16a34a; color: white; }
.btn-danger { background: #dc2626; color: white; }
.btn-outline {
  background: transparent;
  border: 1px solid var(--color-border, #cbd5e1);
  color: var(--color-text, #0f172a);
}

.alert {
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
}

.alert-success { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
.alert-error { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }

.loading-state, .empty-state {
  padding: 3rem 1rem;
  text-align: center;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
