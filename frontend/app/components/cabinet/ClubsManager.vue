<script setup lang="ts">
import { useAdminApi } from "~/api/admin"

const { basePath = "/admin/clubs" } = defineProps<{ basePath?: string }>()

useHead({
  title: "Klublar boshqaruvi",
})

const adminApi = useAdminApi()

const clubs = ref<any[]>([])
const isLoading = ref(true)
const searchQuery = ref("")
const selectedStatus = ref("")
const selectedCategory = ref("")
const totalCount = ref(0)
const errorMessage = ref("")

const fetchClubs = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = {}
    if (searchQuery.value) params.query = searchQuery.value
    if (selectedStatus.value) params.status = selectedStatus.value
    if (selectedCategory.value) params.category = selectedCategory.value

    const res = await adminApi.getClubs(params)
    clubs.value = res.results || res.data || res || []
    totalCount.value = res.count || clubs.value.length
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
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

onMounted(() => {
  void fetchClubs()
})
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Klublar boshqaruvi</h1>
        <p class="page-subtitle">Barcha o'yin klublarini boshqarish va yangi klub qo'shish</p>
      </div>
      <NuxtLink :to="`${basePath}/new`" class="primary-button create-btn">
        <span>➕ Klub qo'shish</span>
      </NuxtLink>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Muassasa nomi yoki telefon bo'yicha qidirish..."
          @keyup.enter="fetchClubs"
        >
      </div>
      <div class="select-box">
        <select v-model="selectedCategory" @change="fetchClubs">
          <option value="">Barcha toifalar</option>
          <option value="GAMING_CLUB">🎮 O'yin klublari</option>
          <option value="BARBERSHOP">💈 Sartaroshxonalar</option>
        </select>
      </div>
      <div class="select-box">
        <select v-model="selectedStatus" @change="fetchClubs">
          <option value="">Barcha holatlar</option>
          <option value="ACTIVE">ACTIVE (Faol)</option>
          <option value="DRAFT">DRAFT (Qoralama)</option>
          <option value="PENDING">PENDING (Kutilmoqda)</option>
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
              <th>Nomi</th>
              <th>Toifa</th>
              <th>Slug (URL)</th>
              <th>Telefon</th>
              <th>Holat</th>
              <th>Tekshiruv</th>
              <th>Reyting</th>
              <th>Amallar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in clubs" :key="c.id">
              <td>
                <div class="club-info">
                  <div class="club-avatar">{{ c.name.slice(0, 1).toUpperCase() }}</div>
                  <div>
                    <span class="club-title">{{ c.name }}</span>
                    <span v-if="c.email" class="club-sub">{{ c.email }}</span>
                  </div>
                </div>
              </td>
              <td>
                <span class="category-pill" :class="c.category === 'BARBERSHOP' ? 'barbershop' : 'gaming'">
                  {{ c.category === 'BARBERSHOP' ? '💈 Sartaroshxona' : '🎮 O\'yin klubi' }}
                </span>
              </td>
              <td><code>{{ c.slug }}</code></td>
              <td>{{ c.phone || "—" }}</td>
              <td>
                <span class="status-badge" :class="c.status.toLowerCase()">
                  {{ c.status }}
                </span>
              </td>
              <td>
                <span class="verified-badge" :class="{ 'is-v': c.is_verified }">
                  {{ c.is_verified ? "✅ Tasdiqlangan" : "⏳ Tasdiqlanmagan" }}
                </span>
              </td>
              <td>⭐ {{ Number(c.rating || 0).toFixed(1) }} ({{ c.review_count || 0 }})</td>
              <td>
                <div class="table-actions">
                  <NuxtLink
                    :to="`${basePath}/${c.id}/edit`"
                    class="action-btn edit"
                    title="Tahrirlash"
                  >
                    ✏️
                  </NuxtLink>
                  <button
                    type="button"
                    class="action-btn delete"
                    title="O'chirish"
                    @click="deleteClub(c)"
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

</style>
