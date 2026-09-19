<script setup lang="ts">
import { useAdminApi } from "~/api/admin"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

useHead({
  title: "To‘lovlar boshqaruvi",
})

const adminApi = useAdminApi()

const payments = ref<any[]>([])
const summary = ref<any>(null)
const isLoading = ref(true)
const errorMessage = ref("")

const statusFilter = ref("")
const providerFilter = ref("")
const searchQuery = ref("")
const totalCount = ref(0)

const fetchPayments = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = { page_size: 50 }
    if (statusFilter.value) params.status = statusFilter.value
    if (providerFilter.value) params.provider = providerFilter.value
    if (searchQuery.value) params.query = searchQuery.value

    const [paymentsRes, summaryRes] = await Promise.all([
      adminApi.getPayments(params),
      adminApi.getPaymentSummary(),
    ])

    payments.value = paymentsRes.results || paymentsRes.data || paymentsRes || []
    totalCount.value = paymentsRes.count || payments.value.length
    summary.value = summaryRes
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const formatPrice = (tiyin: number) => {
  const sum = Math.round((tiyin || 0) / 100)
  return new Intl.NumberFormat("uz-UZ").format(sum) + " so'm"
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " " + d.toLocaleDateString()
}

onMounted(() => {
  void fetchPayments()
})
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">To'lovlar va Tranzaksiyalar</h1>
        <p class="page-subtitle">Barcha to'lov tranzaksiyalari, obunalar va moliyaviy hisobotlar</p>
      </div>
      <button type="button" class="primary-button" :disabled="isLoading" @click="fetchPayments">
        <span>🔄 Yangilash</span>
      </button>
    </div>

    <!-- Summary KPI Cards -->
    <div class="summary-cards-grid">
      <div class="summary-card">
        <span class="sc-label">Jami tushum (Paid)</span>
        <span class="sc-value success">{{ formatPrice(summary?.total_paid_sum_tiyin || 0) }}</span>
        <span class="sc-sub">{{ summary?.total_paid_count || 0 }} ta muvaffaqiyatli to'lov</span>
      </div>
      <div class="summary-card">
        <span class="sc-label">Kutilayotgan to'lovlar</span>
        <span class="sc-value warning">{{ summary?.total_pending_count || 0 }} ta</span>
        <span class="sc-sub">Jarayonda bo'lgan tranzaksiyalar</span>
      </div>
      <div class="summary-card">
        <span class="sc-label">Muvaffaqiyatsiz</span>
        <span class="sc-value danger">{{ summary?.total_failed_count || 0 }} ta</span>
        <span class="sc-sub">Xatolik yoki bekor qilingan</span>
      </div>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="search-wrap">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Mijoz ismi, telefon yoki tranzaksiya ID..."
          @keyup.enter="fetchPayments"
        >
      </div>
      <div class="select-wrap">
        <select v-model="statusFilter" @change="fetchPayments">
          <option value="">Barcha holatlar</option>
          <option value="PAID">PAID (To'langan)</option>
          <option value="PENDING">PENDING (Kutilmoqda)</option>
          <option value="FAILED">FAILED (Xatolik)</option>
          <option value="CANCELLED">CANCELLED (Bekor qilingan)</option>
          <option value="REFUNDED">REFUNDED (Qaytarilgan)</option>
        </select>
      </div>
      <div class="select-wrap">
        <select v-model="providerFilter" @change="fetchPayments">
          <option value="">Barcha provayderlar</option>
          <option value="payme">Payme</option>
          <option value="click">Click</option>
          <option value="manual">Manual</option>
        </select>
      </div>
      <button type="button" class="secondary-button" @click="fetchPayments">Qidirish</button>
    </div>

    <!-- Table -->
    <div v-if="isLoading" class="loading-box">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <div v-else-if="errorMessage" class="error-banner">
      <p>{{ errorMessage }}</p>
      <button type="button" class="secondary-button" @click="fetchPayments">Qayta urinish</button>
    </div>

    <div v-else class="table-card">
      <div v-if="!payments.length" class="empty-state">
        To'lovlar topilmadi.
      </div>

      <div v-else class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Tranzaksiya ID</th>
              <th>Mijoz</th>
              <th>Tarif</th>
              <th>Provayder</th>
              <th>Summa</th>
              <th>Holat</th>
              <th>To'langan vaqt</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in payments" :key="p.id">
              <td>
                <code>#{{ (p.id || '').slice(0, 8) }}</code>
              </td>
              <td>
                <div class="customer-info">
                  <span class="c-name">{{ p.user?.profile?.full_name || p.user?.username || "Foydalanuvchi" }}</span>
                  <span class="c-phone">{{ p.user?.phone || "—" }}</span>
                </div>
              </td>
              <td>
                <span class="plan-tag">{{ p.plan?.name || "Tarif" }}</span>
              </td>
              <td>
                <span class="provider-badge">{{ p.provider }}</span>
              </td>
              <td>
                <span class="price-val">{{ formatPrice(p.amount_tiyin) }}</span>
              </td>
              <td>
                <span class="status-badge" :class="p.status.toLowerCase()">
                  {{ p.status }}
                </span>
              </td>
              <td>{{ formatDate(p.paid_at || p.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
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

.summary-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 20px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sc-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.sc-value {
  font-size: 22px;
  font-weight: 800;
}

.sc-value.success { color: #10b981; }
.sc-value.warning { color: #f59e0b; }
.sc-value.danger { color: #ef4444; }

.sc-sub {
  font-size: 11px;
  color: var(--muted);
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

.search-wrap {
  flex: 1;
  min-width: 240px;
}

.search-wrap input, .select-wrap select {
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

.customer-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.c-name {
  font-weight: 600;
}

.c-phone {
  font-size: 11px;
  color: var(--muted);
}

.plan-tag {
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--control);
  border: 1px solid var(--border);
  font-size: 11px;
  font-weight: 600;
}

.provider-badge {
  text-transform: uppercase;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
}

.price-val {
  font-weight: 800;
  color: var(--accent);
}

.status-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.status-badge.paid { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-badge.pending { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.status-badge.failed, .status-badge.cancelled { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.status-badge.refunded { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }

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
</style>
