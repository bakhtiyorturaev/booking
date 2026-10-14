<script setup lang="ts">
import VenueBillingBadge from "~/components/cabinet/VenueBillingBadge.vue"
import { useAdminApi } from "~/api/admin"
import type { ServiceTypeManagementItem } from "~/api/serviceTypes"
import { serviceTreeOptions } from "~/utils/serviceTree"

definePageMeta({
  alias: ["/site/staff/panel/clubs", "/site/client/panel/clubs"],
  layout: "admin",
  middleware: ["admin"],
})

useHead({
  title: "Xizmatlar",
})

const cabinetPath = useCabinetPath()
const adminApi = useAdminApi()
const route = useRoute()
const categoryLabels: Record<string, string> = { GAMING_CLUB: "O‘yin klubi", BARBERSHOP: "Sartaroshxona", BILLIARDS: "Bilyard", OTHER: "Boshqa xizmat" }
const { statusLabel } = useCabinetLabels()

const { isStaff: isPlatformAdmin } = useCabinetAccess()

const services = ref<ServiceTypeManagementItem[]>([])
const serviceChoices = computed(() => serviceTreeOptions(services.value.filter(service => service.is_active)))
const clubs = ref<any[]>([])
const billingStatuses = useCabinetBillingCache()
const isLoading = ref(true)
const searchQuery = ref("")
const selectedStatus = ref("")
const selectedCategory = ref("")
const totalCount = ref(0)
const errorMessage = ref("")

// Pagination
const page = ref(1)
const hasNextPage = ref(false)
watch([searchQuery, selectedStatus, selectedCategory], () => { page.value = 1 }, { flush: "sync" })

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

const toggleClubStatus = async (club: any) => {
  const nextStatus = club.status === "ACTIVE" ? "INACTIVE" : "ACTIVE"
  try {
    await adminApi.updateClub(club.id, { status: nextStatus })
    await fetchClubs()
  } catch (err) {
    console.error("Failed to toggle status", err)
  }
}

const deleteClub = async (club: any) => {
  if (!confirm(`"${club.name}" xizmatini nofaol qilmoqchimisiz?`)) return
  try {
    await adminApi.deleteClub(club.id)
    await fetchClubs()
  } catch (err) {
    console.error("Failed to delete club", err)
  }
}

onMounted(async () => {
  if (isPlatformAdmin.value && typeof route.query.owner === "string") {
    await navigateTo({ path: cabinetPath("/clubs/new"), query: { owner: route.query.owner } }, { replace: true })
    return
  }
  try { services.value = await adminApi.getServiceTypes() } catch (error) { errorMessage.value = cabinetErrorMessage(error) }
  if (typeof route.query.query === "string") searchQuery.value = route.query.query
  await fetchClubs()
})
</script>

<template>
  <div class="admin-page">
    <!-- Filters Bar -->
    <div class="filter-bar cabinet-list-toolbar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Xizmat nomi yoki telefon bo'yicha qidirish..."
          @keyup.enter="fetchClubs"
         aria-label="Xizmat nomi yoki telefon bo'yicha qidirish...">
      </div>
      <div class="select-box">
        <select v-model="selectedCategory" @change="fetchClubs" aria-label="Xizmat turi"><option value="">Barcha xizmatlar</option><option v-for="service in serviceChoices" :key="service.id" :value="service.id">{{ service.label }}</option></select>
      </div>
      <div class="select-box">
        <select v-model="selectedStatus" @change="fetchClubs" aria-label="Holat">
          <option value="">Barcha holatlar</option>
          <option value="ACTIVE">Faol</option>
          <option value="INACTIVE">Nofaol</option>
        </select>
      </div>
      <button type="button" class="secondary-button" @click="fetchClubs">
        Qidirish
      </button>
      <NuxtLink v-if="isPlatformAdmin" :to="cabinetPath('/clubs/new')" class="primary-button create-btn">
        <CabinetIcon name="plus" /> Xizmat qo‘shish
      </NuxtLink>
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
        Xizmatlar topilmadi.
      </div>
      <div v-else class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th scope="col">Nomi</th>
              <th scope="col" v-if="isPlatformAdmin">Egasi</th>
              <th scope="col">Toifa</th>
              <th scope="col">Telefon</th>
              <th scope="col">To‘lov muddati</th>
              <th scope="col">Holat</th>
              <th scope="col">Reyting</th>
              <th v-if="isPlatformAdmin" scope="col">Amallar</th>
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
              <td data-label="Telefon">{{ c.phone || "—" }}</td>
              <td data-label="To‘lov muddati"><VenueBillingBadge v-if="c.billing" :billing="c.billing" :club-id="c.id" /><span v-else>—</span></td>
              <td data-label="Holat">
                <span class="status-badge" :class="c.status.toLowerCase()">
                  {{ statusLabel(c.status) }}
                </span>
              </td>
              <td data-label="Reyting"><CabinetIcon name="star" /> {{ Number(c.rating || 0).toFixed(1) }} ({{ c.review_count || 0 }})</td>
              <td v-if="isPlatformAdmin" data-label="Amallar">
                <div class="table-actions">
                  <NuxtLink
                    :to="cabinetPath(`/clubs/${c.id}/edit`)"
                    class="action-btn edit"
                    title="Tahrirlash"
                    aria-label="Tahrirlash"
                  >
                    <CabinetIcon name="edit" />
                  </NuxtLink>
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
  display: inline-flex;
  align-items: center;
  color: inherit;
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
