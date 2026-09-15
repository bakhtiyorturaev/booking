<script setup lang="ts">
import { useAdminApi } from "~/api/admin"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

const adminApi = useAdminApi()

const reviews = ref<any[]>([])
const clubs = ref<any[]>([])
const isLoading = ref(true)
const errorMessage = ref("")

const selectedClubId = ref("")
const visibilityFilter = ref("")
const ratingFilter = ref("")
const searchQuery = ref("")
const totalCount = ref(0)

const fetchClubs = async () => {
  try {
    const res = await adminApi.getClubs({ page_size: 100 })
    clubs.value = res.results || res.data || res || []
  } catch (err) {
    console.error("Failed to load clubs", err)
  }
}

const fetchReviews = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = { page_size: 50 }
    if (selectedClubId.value) params.club_id = selectedClubId.value
    if (visibilityFilter.value) params.is_visible = visibilityFilter.value
    if (ratingFilter.value) params.rating = ratingFilter.value
    if (searchQuery.value) params.query = searchQuery.value

    const res = await adminApi.getReviews(params)
    reviews.value = res.results || res.data || res || []
    totalCount.value = res.count || reviews.value.length
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const toggleVisibility = async (r: any) => {
  try {
    await adminApi.toggleReviewVisibility(r.id)
    await fetchReviews()
  } catch (err) {
    console.error("Failed to toggle visibility", err)
  }
}

const deleteReview = async (r: any) => {
  if (!confirm("Ushbu sharhni butunlay o'chirmoqchimisiz?")) return
  try {
    await adminApi.deleteReview(r.id)
    await fetchReviews()
  } catch (err) {
    console.error("Failed to delete review", err)
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return "—"
  const d = new Date(dateStr)
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

onMounted(() => {
  void fetchClubs()
  void fetchReviews()
})
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Sharhlar Moderatsiyasi</h1>
        <p class="page-subtitle">Klublar uchun qoldirilgan barcha sharhlar va ularning moderatsiyasi</p>
      </div>
      <button type="button" class="primary-button" :disabled="isLoading" @click="fetchReviews">
        <span>🔄 Yangilash</span>
      </button>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="search-wrap">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Izoh matni yoki mijoz ismi..."
          @keyup.enter="fetchReviews"
        >
      </div>
      <div class="select-wrap">
        <select v-model="selectedClubId" @change="fetchReviews">
          <option value="">Barcha klublar</option>
          <option v-for="c in clubs" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="select-wrap">
        <select v-model="visibilityFilter" @change="fetchReviews">
          <option value="">Barcha holatlar</option>
          <option value="true">Ko'rsatilgan (Faol)</option>
          <option value="false">Yashirilgan (Moderatsiyada)</option>
        </select>
      </div>
      <div class="select-wrap">
        <select v-model="ratingFilter" @change="fetchReviews">
          <option value="">Barcha baholar</option>
          <option value="5">⭐⭐⭐⭐⭐ (5)</option>
          <option value="4">⭐⭐⭐⭐ (4)</option>
          <option value="3">⭐⭐⭐ (3)</option>
          <option value="2">⭐⭐ (2)</option>
          <option value="1">⭐ (1)</option>
        </select>
      </div>
      <button type="button" class="secondary-button" @click="fetchReviews">Qidirish</button>
    </div>

    <!-- Table -->
    <div v-if="isLoading" class="loading-box">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <div v-else-if="errorMessage" class="error-banner">
      <p>{{ errorMessage }}</p>
      <button type="button" class="secondary-button" @click="fetchReviews">Qayta urinish</button>
    </div>

    <div v-else class="table-card">
      <div v-if="!reviews.length" class="empty-state">
        Sharhlar topilmadi.
      </div>

      <div v-else class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Muallif</th>
              <th>Klub</th>
              <th>Baho</th>
              <th>Izoh</th>
              <th>Holat</th>
              <th>Sana</th>
              <th>Amallar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reviews" :key="r.id">
              <td>
                <span class="author-name">{{ r.user?.profile?.full_name || r.user?.username || "Mijoz" }}</span>
              </td>
              <td>
                <span class="club-badge">{{ r.club?.name || "Klub" }}</span>
              </td>
              <td>
                <div class="rating-stars">
                  <span v-for="s in 5" :key="s" :class="{ 'gold': s <= r.rating }">★</span>
                </div>
              </td>
              <td>
                <p class="comment-text">"{{ r.comment || 'Izohsiz' }}"</p>
              </td>
              <td>
                <span class="status-badge" :class="r.is_visible ? 'visible' : 'hidden'">
                  {{ r.is_visible ? "Ko'rsatilgan" : "Yashirilgan" }}
                </span>
              </td>
              <td>{{ formatDate(r.created_at) }}</td>
              <td>
                <div class="action-buttons-inline">
                  <button
                    type="button"
                    class="btn-act"
                    :class="r.is_visible ? 'hide' : 'show'"
                    :title="r.is_visible ? 'Yashirish' : 'Ko\'rsatish'"
                    @click="toggleVisibility(r)"
                  >
                    {{ r.is_visible ? '👁️ Yashirish' : '✅ Ko\'rsatish' }}
                  </button>
                  <button
                    type="button"
                    class="btn-act delete"
                    title="O'chirish"
                    @click="deleteReview(r)"
                  >
                    🗑️
                  </button>
                </div>
              </td>
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
  min-width: 200px;
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

.author-name {
  font-weight: 600;
}

.club-badge {
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--control);
  border: 1px solid var(--border);
  font-size: 11px;
  font-weight: 600;
}

.rating-stars {
  color: #4b5563;
  font-size: 14px;
}

.rating-stars .gold {
  color: #f59e0b;
}

.comment-text {
  margin: 0;
  max-width: 320px;
  line-height: 1.4;
  color: var(--text);
}

.status-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
}

.status-badge.visible { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-badge.hidden { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

.action-buttons-inline {
  display: flex;
  gap: 6px;
}

.btn-act {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--control);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-act.hide { color: #f59e0b; border-color: #f59e0b; }
.btn-act.show { color: #10b981; border-color: #10b981; }
.btn-act.delete:hover { color: #ef4444; border-color: #ef4444; }

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
