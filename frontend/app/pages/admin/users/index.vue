<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
import { useAuth } from "~/composables/useAuth"

definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

useHead({
  title: "Foydalanuvchilar va Xodimlar",
})

const { user: currentUser } = useAuth()
const adminApi = useAdminApi()

const users = ref<any[]>([])
const isLoading = ref(true)
const errorMessage = ref("")

const roleFilter = ref("")
const statusFilter = ref("")
const searchQuery = ref("")
const totalCount = ref(0)

// Role Change Modal
const showRoleModal = ref(false)
const selectedUser = ref<any>(null)
const newRole = ref("CUSTOMER")
const isSavingRole = ref(false)
const roleModalError = ref("")

const fetchUsers = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const params: Record<string, any> = { page_size: 50 }
    if (roleFilter.value) params.role = roleFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    if (searchQuery.value) params.query = searchQuery.value

    const res = await adminApi.getUsers(params)
    users.value = res.results || res.data || res || []
    totalCount.value = res.count || users.value.length
  } catch (err: any) {
    errorMessage.value = err?.message || "Server bilan bog'lanishda xatolik yuz berdi"
  } finally {
    isLoading.value = false
  }
}

const openRoleModal = (u: any) => {
  selectedUser.value = u
  newRole.value = u.role || "CUSTOMER"
  roleModalError.value = ""
  showRoleModal.value = true
}

const saveRole = async () => {
  if (!selectedUser.value) return
  isSavingRole.value = true
  roleModalError.value = ""
  try {
    await adminApi.setUserRole(selectedUser.value.id, newRole.value)
    showRoleModal.value = false
    await fetchUsers()
  } catch (err: any) {
    roleModalError.value = err?.data?.message || err?.message || "Rolni o'zgartirishda xatolik yuz berdi"
  } finally {
    isSavingRole.value = false
  }
}

const toggleUserStatus = async (u: any) => {
  if (u.id === currentUser.value?.id) {
    alert("O'z hisobingizni bloklay olmaysiz!")
    return
  }
  const actionName = u.status === "ACTIVE" ? "bloklamoqchimisiz" : "blokdan chiqarmoqchimisiz"
  if (!confirm(`"${u.username}" foydalanuvchisini ${actionName}?`)) return

  try {
    await adminApi.toggleUserStatus(u.id)
    await fetchUsers()
  } catch (err: any) {
    alert(err?.data?.message || err?.message || "Holatni o'zgartirishda xatolik yuz berdi")
  }
}

onMounted(() => {
  void fetchUsers()
})
</script>

<template>
  <div class="admin-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Foydalanuvchilar va Rollar</h1>
        <p class="page-subtitle">Platforma foydalanuvchilari, moderatorlar va xodimlar boshqaruvi</p>
      </div>
      <button type="button" class="primary-button" :disabled="isLoading" @click="fetchUsers">
        <span>🔄 Yangilash</span>
      </button>
    </div>

    <!-- Filters Bar -->
    <div class="filter-bar">
      <div class="search-wrap">
        <input
          v-model="searchQuery"
          type="search"
          placeholder="Ism, username yoki telefon raqami..."
          @keyup.enter="fetchUsers"
        >
      </div>
      <div class="select-wrap">
        <select v-model="roleFilter" @change="fetchUsers">
          <option value="">Barcha rollar</option>
          <option value="ADMIN">ADMIN (Administrator)</option>
          <option value="MODERATOR">MODERATOR (Xodim)</option>
          <option value="CUSTOMER">CUSTOMER (Mijoz)</option>
        </select>
      </div>
      <div class="select-wrap">
        <select v-model="statusFilter" @change="fetchUsers">
          <option value="">Barcha holatlar</option>
          <option value="ACTIVE">ACTIVE (Faol)</option>
          <option value="BLOCKED">BLOCKED (Bloklangan)</option>
        </select>
      </div>
      <button type="button" class="secondary-button" @click="fetchUsers">Qidirish</button>
    </div>

    <!-- Table -->
    <div v-if="isLoading" class="loading-box">
      <span class="auth-spinner" />
      <p>Yuklanmoqda...</p>
    </div>

    <div v-else-if="errorMessage" class="error-banner">
      <p>{{ errorMessage }}</p>
      <button type="button" class="secondary-button" @click="fetchUsers">Qayta urinish</button>
    </div>

    <div v-else class="table-card">
      <div v-if="!users.length" class="empty-state">
        Foydalanuvchilar topilmadi.
      </div>

      <div v-else class="table-container">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Foydalanuvchi</th>
              <th>Username</th>
              <th>Telefon</th>
              <th>Rol</th>
              <th>Holat</th>
              <th>Telegram ID</th>
              <th>Amallar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>
                <div class="user-cell">
                  <div class="user-avatar-circle">
                    {{ (u.profile?.full_name || u.username || "U").slice(0, 1).toUpperCase() }}
                  </div>
                  <div>
                    <span class="u-name">{{ u.profile?.full_name || u.username }}</span>
                    <span v-if="u.profile?.city" class="u-city">📍 {{ u.profile.city }}</span>
                  </div>
                </div>
              </td>
              <td><code>@{{ u.username }}</code></td>
              <td>{{ u.phone || "—" }}</td>
              <td>
                <span class="role-badge" :class="u.role.toLowerCase()">
                  {{ u.role }}
                </span>
              </td>
              <td>
                <span class="status-badge" :class="u.status.toLowerCase()">
                  {{ u.status }}
                </span>
              </td>
              <td>{{ u.telegram_user_id || "—" }}</td>
              <td>
                <div class="action-buttons-inline">
                  <button
                    type="button"
                    class="btn-act role-btn"
                    title="Rolni o'zgartirish"
                    @click="openRoleModal(u)"
                  >
                    👑 Rol
                  </button>
                  <button
                    v-if="u.id !== currentUser?.id"
                    type="button"
                    class="btn-act"
                    :class="u.status === 'ACTIVE' ? 'block-btn' : 'unblock-btn'"
                    :title="u.status === 'ACTIVE' ? 'Bloklash' : 'Blokdan chiqarish'"
                    @click="toggleUserStatus(u)"
                  >
                    {{ u.status === 'ACTIVE' ? '🚫 Bloklash' : '✅ Faollashtirish' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Role Modal -->
    <Teleport to="body">
      <div v-if="showRoleModal" class="modal-backdrop" @click.self="showRoleModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>Foydalanuvchi rolini o'zgartirish</h3>
            <button type="button" class="modal-close-btn" @click="showRoleModal = false">✕</button>
          </div>

          <form class="modal-form" @submit.prevent="saveRole">
            <p v-if="roleModalError" class="form-error">{{ roleModalError }}</p>

            <div class="user-preview">
              <strong>{{ selectedUser?.profile?.full_name || selectedUser?.username }}</strong>
              <span>(@{{ selectedUser?.username }})</span>
            </div>

            <div class="form-group">
              <label>Yangi rol</label>
              <select v-model="newRole">
                <option value="CUSTOMER">CUSTOMER (Oddiy mijoz)</option>
                <option value="MODERATOR">MODERATOR (Xodim - Boshqaruv huquqi bilan)</option>
                <option value="ADMIN">ADMIN (To'liq administrator)</option>
              </select>
            </div>

            <div class="modal-actions">
              <button type="button" class="secondary-button" @click="showRoleModal = false">Bekor qilish</button>
              <button type="submit" class="primary-button" :disabled="isSavingRole">
                {{ isSavingRole ? "Saqlanmoqda..." : "Saqlash" }}
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

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar-circle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent) 0%, #0088cc 100%);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
}

.u-name {
  font-weight: 600;
  display: block;
}

.u-city {
  font-size: 11px;
  color: var(--muted);
}

.role-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.role-badge.admin { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.role-badge.moderator { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.role-badge.customer { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }

.status-badge {
  padding: 3px 8px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.status-badge.active { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-badge.blocked { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

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

.btn-act.role-btn:hover { border-color: var(--accent); color: var(--accent); }
.btn-act.block-btn:hover { border-color: #ef4444; color: #ef4444; }
.btn-act.unblock-btn:hover { border-color: #10b981; color: #10b981; }

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

.user-preview {
  padding: 12px;
  background: var(--control);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
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
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.form-group select {
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
</style>
