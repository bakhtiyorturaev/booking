<script setup lang="ts">
import { useAdminApi } from "~/api/admin"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

const adminApi = useAdminApi()

const stats = ref<any>(null)
const isLoading = ref(true)
const errorMessage = ref("")

const fetchStats = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const data = await adminApi.getStats()
    stats.value = data
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const handleCheckIn = async (bookingId: string) => {
  try {
    await adminApi.checkInBooking(bookingId)
    await fetchStats()
  } catch (err) {
    console.error("Check-in failed", err)
  }
}

const handleComplete = async (bookingId: string) => {
  try {
    await adminApi.completeBooking(bookingId)
    await fetchStats()
  } catch (err) {
    console.error("Complete failed", err)
  }
}

const formatPrice = (tiyin: number) => {
  const sum = Math.round((tiyin || 0) / 100)
  return new Intl.NumberFormat("uz-UZ").format(sum) + " so'm"
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " " + d.toLocaleDateString()
}

onMounted(() => {
  void fetchStats()
})
</script>

<template>
  <div class="admin-dashboard">
    <!-- Page Header -->
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">Boshqaruv paneli</h1>
        <p class="page-subtitle">Tizim holati va umumiy ko'rsatkichlar monitoringi</p>
      </div>
      <button
        type="button"
        class="primary-button refresh-btn"
        :disabled="isLoading"
        @click="fetchStats"
      >
        <span>🔄 Yangilash</span>
      </button>
    </div>

    <!-- Error state -->
    <div v-if="errorMessage" class="error-banner">
      <p>{{ errorMessage }}</p>
      <button type="button" class="secondary-button" @click="fetchStats">
        Qayta urinish
      </button>
    </div>

    <div v-else-if="isLoading" class="loading-container">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <div v-else class="dashboard-content">
      <!-- KPI Metric Cards Grid -->
      <div class="kpi-grid">
        <!-- Card 1: Clubs -->
        <div class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-icon clubs-bg">🎮</span>
            <span class="kpi-tag active">{{ stats?.clubs?.active || 0 }} faol</span>
          </div>
          <div class="kpi-value">{{ stats?.clubs?.total || 0 }}</div>
          <div class="kpi-label">Jami klublar</div>
        </div>

        <!-- Card 2: Today Bookings -->
        <div class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-icon bookings-bg">📅</span>
            <span class="kpi-tag highlight">{{ stats?.bookings?.active_now || 0 }} hozir o'ynayapti</span>
          </div>
          <div class="kpi-value">{{ stats?.bookings?.today || 0 }}</div>
          <div class="kpi-label">Bugungi bronlar</div>
        </div>

        <!-- Card 3: Today Revenue -->
        <div class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-icon revenue-bg">💳</span>
            <span class="kpi-tag success">Jami: {{ formatPrice(stats?.revenue?.total_tiyin || 0) }}</span>
          </div>
          <div class="kpi-value">{{ formatPrice(stats?.revenue?.today_tiyin || 0) }}</div>
          <div class="kpi-label">Bugungi tushum</div>
        </div>

        <!-- Card 4: Active Users -->
        <div class="kpi-card">
          <div class="kpi-top">
            <span class="kpi-icon users-bg">👥</span>
            <span class="kpi-tag staff">{{ stats?.users?.staff || 0 }} xodim</span>
          </div>
          <div class="kpi-value">{{ stats?.users?.active || 0 }} / {{ stats?.users?.total || 0 }}</div>
          <div class="kpi-label">Faol foydalanuvchilar</div>
        </div>
      </div>

      <!-- Quick Actions Grid -->
      <div class="quick-actions-bar">
        <NuxtLink to="/admin/clubs" class="quick-action-btn">
          <span class="qa-icon">➕</span>
          <span>Muassasalar</span>
        </NuxtLink>
        <NuxtLink to="/admin/branches" class="quick-action-btn">
          <span class="qa-icon">🏢</span>
          <span>Filiallar</span>
        </NuxtLink>
        <NuxtLink to="/admin/barbers" class="quick-action-btn">
          <span class="qa-icon">💈</span>
          <span>Sartaroshlar</span>
        </NuxtLink>
        <NuxtLink to="/admin/bookings" class="quick-action-btn">
          <span class="qa-icon">⚡</span>
          <span>Bronlar</span>
        </NuxtLink>
        <NuxtLink to="/admin/reviews" class="quick-action-btn">
          <span class="qa-icon">⭐</span>
          <span>Sharhlar</span>
        </NuxtLink>
      </div>

      <!-- Live Recent Bookings Table -->
      <div class="dashboard-section">
        <div class="section-top">
          <h2 class="section-title">Oxirgi bronlar</h2>
          <NuxtLink to="/admin/bookings" class="section-link">Barchasini ko'rish →</NuxtLink>
        </div>

        <div v-if="!stats?.recent_bookings?.length" class="empty-box">
          Hozircha bronlar mavjud emas.
        </div>

        <div v-else class="table-container">
          <table class="admin-table">
            <thead>
              <tr>
                <th>Mijoz</th>
                <th>Klub / Filial</th>
                <th>Zona</th>
                <th>Vaqt</th>
                <th>Summa</th>
                <th>Holat</th>
                <th>Amallar</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="b in stats.recent_bookings" :key="b.id">
                <td>
                  <div class="customer-cell">
                    <span class="customer-name">{{ b.user_name }}</span>
                    <span class="customer-phone">{{ b.user_phone || "—" }}</span>
                  </div>
                </td>
                <td>
                  <div class="club-cell">
                    <span class="club-title">{{ b.club_name }}</span>
                    <span class="branch-subtitle">{{ b.branch_name }}</span>
                  </div>
                </td>
                <td>
                  <span class="zone-badge">{{ b.zone_name }}</span>
                </td>
                <td>
                  <span class="time-text">{{ formatDate(b.starts_at) }}</span>
                </td>
                <td>
                  <span class="price-text">{{ formatPrice(b.total_price_tiyin) }}</span>
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
                      class="btn-action checkin"
                      title="Check-in"
                      @click="handleCheckIn(b.id)"
                    >
                      Check-in
                    </button>
                    <button
                      v-if="b.status === 'CHECKED_IN'"
                      type="button"
                      class="btn-action complete"
                      title="Tugatish"
                      @click="handleComplete(b.id)"
                    >
                      Tugatish
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Recent Reviews Widget -->
      <div class="dashboard-section">
        <div class="section-top">
          <h2 class="section-title">Yangi sharhlar</h2>
          <NuxtLink to="/admin/reviews" class="section-link">Moderatsiya qilish →</NuxtLink>
        </div>

        <div v-if="!stats?.recent_reviews?.length" class="empty-box">
          Sharhlar mavjud emas.
        </div>

        <div v-else class="reviews-grid">
          <div v-for="r in stats.recent_reviews" :key="r.id" class="review-widget-card">
            <div class="review-card-top">
              <span class="review-author">{{ r.user_name }}</span>
              <div class="review-stars">
                <span v-for="s in 5" :key="s" :class="{ 'gold': s <= r.rating }">★</span>
              </div>
            </div>
            <p class="review-comment">"{{ r.comment || 'Izohsiz' }}"</p>
            <div class="review-card-footer">
              <span class="review-club">{{ r.club_name }}</span>
              <span class="review-visibility-badge" :class="{ 'visible': r.is_visible }">
                {{ r.is_visible ? "Ko'rsatilgan" : "Yashirilgan" }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.kpi-card {
  padding: 20px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
}

.kpi-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 20px;
}

.clubs-bg { background: rgba(32, 199, 244, 0.15); color: #20c7f4; }
.bookings-bg { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.revenue-bg { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.users-bg { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }

.kpi-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 20px;
}

.kpi-tag.active { background: rgba(32, 199, 244, 0.12); color: var(--accent); }
.kpi-tag.highlight { background: rgba(16, 185, 129, 0.12); color: #10b981; }
.kpi-tag.success { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
.kpi-tag.staff { background: rgba(139, 92, 246, 0.12); color: #8b5cf6; }

.kpi-value {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.kpi-label {
  font-size: 13px;
  color: var(--muted);
}

.quick-actions-bar {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.quick-action-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.15s ease;
}

.quick-action-btn:hover {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
}

.qa-icon {
  font-size: 18px;
}

.dashboard-section {
  background: var(--surface);
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  margin: 0;
  font-size: 17px;
  font-weight: 750;
}

.section-link {
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
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
}

.admin-table td {
  padding: 14px;
  border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
  vertical-align: middle;
}

.customer-cell, .club-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.customer-name, .club-title {
  font-weight: 600;
}

.customer-phone, .branch-subtitle {
  font-size: 11px;
  color: var(--muted);
}

.zone-badge {
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--control);
  border: 1px solid var(--border);
  font-size: 11px;
  font-weight: 600;
}

.price-text {
  font-weight: 700;
  color: var(--accent);
}

.status-badge {
  padding: 4px 10px;
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

.action-buttons-inline {
  display: flex;
  gap: 6px;
}

.btn-action {
  padding: 4px 10px;
  border-radius: 6px;
  border: none;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.btn-action.checkin {
  background: #3b82f6;
  color: #fff;
}

.btn-action.complete {
  background: #10b981;
  color: #fff;
}

.reviews-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}

.review-widget-card {
  padding: 14px;
  background: var(--control);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.review-author {
  font-weight: 600;
  font-size: 13px;
}

.review-stars {
  color: #4b5563;
  font-size: 13px;
}

.review-stars .gold {
  color: #f59e0b;
}

.review-comment {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
  font-style: italic;
}

.review-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
}

.review-club {
  color: var(--text);
  font-weight: 600;
}

.review-visibility-badge {
  color: #ef4444;
  font-weight: 600;
}

.review-visibility-badge.visible {
  color: #10b981;
}

.empty-box {
  padding: 30px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
  color: var(--muted);
}
</style>
