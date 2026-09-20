<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faCalendar,
  faCrown,
  faHeart,
  faLocationDot,
  faPen,
  faPhone,
  faRightFromBracket,
  faShieldHalved,
  faUser,
} from "@fortawesome/free-solid-svg-icons"

import { useAuthApi } from "~/api/auth"
import { useSubscription } from "~/composables/useSubscription"
import { useFavorites } from "~/composables/useFavorites"
import BranchCard from "~/components/catalog/BranchCard.vue"
import { ApiRequestError } from "~/types/api"
import type { BranchListSummary } from "~/types/club"

definePageMeta({
  layout: "customer",
  middleware: "auth",
})

const auth = useAuth()
const authApi = useAuthApi()
const subscriptionState = useSubscription()
const favorites = useFavorites()
const { user } = auth
const { locale, load, t } = useTranslations()

await load()
await subscriptionState.load().catch(() => null)

const profileCodes = [
  "auth.phone_number", "auth.city", "auth.birth_date", "nav.logout",
  "profile.personal_details", "common.edit", "common.save", "common.cancel",
  "profile.subscription_paid", "profile.subscription_free",
]
if (profileCodes.some(code => t(code) === code)) {
  await load(locale.value, true).catch(() => undefined)
}

useHead({
  title: computed(() => t("profile.title") || "Mening profilim"),
})

// Always reload favorites on client mount to ensure fresh state
onMounted(async () => {
  await favorites.load(true).catch(() => null)
})

const editing = ref(false)
const pending = ref(false)
const logoutPending = ref(false)
const messageSuccess = ref(false)
const { message, show: showMessage, clear: clearMessage } = useTimedMessage()

const form = reactive({
  full_name: "",
  city: "",
  birth_date: "",
})

const profile = computed(() => user.value?.profile)
const fullName = computed(() => profile.value?.full_name || user.value?.full_name || "")
const displayName = computed(() => {
  return fullName.value || user.value?.phone || user.value?.username || t("nav.profile")
})
const accountDetail = computed(() => {
  return user.value?.phone || user.value?.username || ""
})

const userInitials = computed(() => {
  const name = (fullName.value || user.value?.username || "").trim()
  if (!name) return ""
  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
})

const resetForm = () => {
  form.full_name = profile.value?.full_name || ""
  form.city = profile.value?.city || ""
  form.birth_date = profile.value?.birth_date || ""
}

const startEditing = () => {
  resetForm()
  clearMessage()
  editing.value = true
}

const cancelEditing = () => {
  editing.value = false
  clearMessage()
}

const saveProfile = async () => {
  pending.value = true
  clearMessage()
  try {
    const response = await authApi.updateProfile({
      ...form,
      birth_date: form.birth_date || null,
    }, locale.value)
    auth.setUser(response.data.user)
    editing.value = false
    messageSuccess.value = true
    showMessage(response.message)
  } catch (error) {
    messageSuccess.value = false
    showMessage(error instanceof ApiRequestError ? error.message : t("common.backend_unavailable"))
  } finally {
    pending.value = false
  }
}

const signOut = async () => {
  logoutPending.value = true
  try {
    await auth.logout()
    await navigateTo("/login")
  } finally {
    logoutPending.value = false
  }
}

const formatDate = (value?: string | null) => {
  if (!value) return ""
  try {
    return new Intl.DateTimeFormat(locale.value, {
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(new Date(value))
  } catch {
    return ""
  }
}

const fields = computed(() => [
  { code: "auth.phone_number", value: user.value?.phone || "", icon: faPhone },
  { code: "auth.city", value: profile.value?.city || "", icon: faLocationDot },
  { code: "auth.birth_date", value: formatDate(profile.value?.birth_date), icon: faCalendar },
])

const favoriteBranches = computed(() => {
  const list: BranchListSummary[] = []
  for (const item of favorites.favoritesList.value) {
    if (!item?.club) continue
    const club = item.club
    if (club.branches && club.branches.length > 0) {
      for (const branch of club.branches) {
        list.push({
          ...branch,
          club: {
            id: club.id,
            name: club.name,
            category: club.category,
            category_display: club.category_display,
            slug: club.slug,
            logo: club.logo,
            rating: club.rating,
            review_count: club.review_count,
          },
          is_favorite: true,
        })
      }
    } else {
      list.push({
        id: club.id,
        name: club.name,
        address: club.description || "",
        full_address: club.description || "",
        city: { id: "", name: "", slug: "" },
        district: null,
        latitude: "0",
        longitude: "0",
        is_24_hours: false,
        service_types: club.service_types || [],
        min_price_tiyin: club.min_price_tiyin || 0,
        cover_image: club.cover || club.logo,
        distance_km: club.distance_km,
        is_favorite: true,
        club: {
          id: club.id,
          name: club.name,
          category: club.category,
          category_display: club.category_display,
          slug: club.slug,
          logo: club.logo,
          rating: club.rating,
          review_count: club.review_count,
        },
      })
    }
  }
  return list
})
</script>

<template>
  <section class="profile-page-wrapper">
    <div class="profile-container">
      <!-- User Summary Header Card -->
      <div class="profile-user-card">
        <div class="profile-user-main">
          <div class="profile-avatar-compact">
            <span v-if="userInitials" class="avatar-initials">{{ userInitials }}</span>
            <FontAwesomeIcon v-else :icon="faUser" />
          </div>
          <div class="profile-user-info">
            <div class="profile-name-row">
              <h1 class="profile-user-name">{{ displayName }}</h1>
              <span v-if="['ADMIN', 'MODERATOR'].includes(user?.role || '')" class="role-badge">
                <FontAwesomeIcon :icon="faShieldHalved" />
                {{ user?.role }}
              </span>
            </div>
            <p v-if="accountDetail" class="profile-user-sub">{{ accountDetail }}</p>
          </div>
        </div>

        <!-- Tariff & Actions Area -->
        <div class="profile-user-actions">
          <!-- Current Tariff Status Badge (In place of old subscription section) -->
          <div class="profile-tariff-badge" :class="{ 'is-premium': subscriptionState.isPaid.value }">
            <FontAwesomeIcon :icon="faCrown" class="tariff-crown-icon" />
            <div class="tariff-badge-text">
              <span class="tariff-label">Tarif:</span>
              <strong class="tariff-value">
                {{ subscriptionState.isPaid.value ? t("profile.subscription_paid") : (t("profile.subscription_free") || "Bepul") }}
              </strong>
            </div>
          </div>

          <!-- Admin Link if Admin/Mod -->
          <NuxtLink
            v-if="['ADMIN', 'MODERATOR'].includes(user?.role || '')"
            to="/admin"
            class="admin-portal-link"
          >
            {{ t("admin.dashboard") }}
          </NuxtLink>

          <!-- Red Logout Button -->
          <button
            type="button"
            class="profile-danger-logout-btn"
            :disabled="logoutPending"
            @click="signOut"
          >
            <FontAwesomeIcon :icon="faRightFromBracket" />
            <span>{{ logoutPending ? t("common.loading") : t("nav.logout") }}</span>
          </button>
        </div>
      </div>

      <!-- Personal Details Card -->
      <article class="profile-section-card">
        <header class="profile-section-header">
          <h2>{{ t("profile.personal_details") }}</h2>
          <button v-if="!editing" type="button" class="profile-edit-btn" @click="startEditing">
            <FontAwesomeIcon :icon="faPen" />
            <span>{{ t("common.edit") }}</span>
          </button>
        </header>

        <form v-if="editing" class="profile-edit-form" @submit.prevent="saveProfile">
          <div class="profile-form-grid">
            <label class="form-field">
              <span class="field-label">{{ t("auth.full_name") }}</span>
              <input v-model="form.full_name" type="text" placeholder="Ism-familiya">
            </label>
            <label class="form-field">
              <span class="field-label">{{ t("auth.city") }}</span>
              <input v-model="form.city" type="text" placeholder="Shahar">
            </label>
            <label class="form-field">
              <span class="field-label">{{ t("auth.birth_date") }}</span>
              <input v-model="form.birth_date" type="date">
            </label>
          </div>
          <p
            v-if="message"
            class="form-message profile-form-message"
            :class="{ success: messageSuccess }"
            role="status"
          >
            {{ message }}
          </p>
          <div class="profile-form-actions">
            <button type="button" class="cancel-btn" @click="cancelEditing">
              {{ t("common.cancel") }}
            </button>
            <button type="submit" class="save-btn" :disabled="pending">
              {{ pending ? t("common.loading") : t("common.save") }}
            </button>
          </div>
        </form>

        <template v-else>
          <p
            v-if="message"
            class="form-message profile-form-message"
            :class="{ success: messageSuccess }"
            role="status"
          >
            {{ message }}
          </p>
          <dl class="profile-fields-grid">
            <div v-for="field in fields" :key="field.code" class="profile-field-box">
              <dt>
                <FontAwesomeIcon :icon="field.icon" class="field-icon" />
                <span>{{ t(field.code) }}</span>
              </dt>
              <dd :class="{ 'is-empty': !field.value }">
                {{ field.value || "—" }}
              </dd>
            </div>
          </dl>
        </template>
      </article>

      <!-- Favorites Section -->
      <article class="profile-section-card">
        <header class="profile-section-header">
          <h2>
            <FontAwesomeIcon :icon="faHeart" class="favorite-heart-icon" />
            <span>{{ t("profile.favorites") }}</span>
            <span v-if="favoriteBranches.length" class="favorites-count-badge">
              {{ favoriteBranches.length }}
            </span>
          </h2>
        </header>

        <div v-if="favorites.loading.value" class="favorites-loading-state">
          <p>{{ t("common.loading") }}</p>
        </div>

        <div v-else-if="favoriteBranches.length" class="profile-favorites-grid">
          <BranchCard
            v-for="branch in favoriteBranches"
            :key="branch.id"
            :branch="branch"
          />
        </div>

        <div v-else class="favorites-empty-state">
          <div class="favorites-empty-icon">
            <FontAwesomeIcon :icon="faHeart" />
          </div>
          <h3>{{ t("profile.no_favorites") }}</h3>
          <p>{{ t("profile.no_favorites_desc") }}</p>
          <NuxtLink to="/" class="favorites-explore-btn">
            {{ t("profile.explore_clubs") }}
          </NuxtLink>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.profile-page-wrapper {
  width: 100%;
  padding: 24px 16px 64px;
}

.profile-container {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* User Card */
.profile-user-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  background: color-mix(in srgb, var(--surface) 90%, transparent);
  backdrop-filter: blur(16px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.profile-user-main {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.profile-avatar-compact {
  width: 54px;
  height: 54px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, color-mix(in srgb, var(--accent) 30%, #3b82f6) 0%, var(--accent) 100%);
  display: grid;
  place-items: center;
  color: #ffffff;
  font-size: 20px;
  font-weight: 800;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--accent) 25%, transparent);
  border: 2px solid color-mix(in srgb, var(--accent) 50%, #ffffff);
}

.avatar-initials {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #ffffff;
}

.profile-user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.profile-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-user-name {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
  color: var(--text);
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.profile-user-sub {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}

.profile-user-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

/* Tariff Badge */
.profile-tariff-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--control) 80%, transparent);
  border: 1px solid var(--panel-border);
  font-size: 12px;
}

.profile-tariff-badge.is-premium {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.35);
  color: #f59e0b;
}

.tariff-crown-icon {
  color: #f59e0b;
  font-size: 13px;
}

.tariff-badge-text {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.tariff-label {
  font-size: 11px;
  color: var(--muted);
}

.tariff-value {
  font-size: 12px;
  font-weight: 750;
  color: var(--text);
}

.profile-tariff-badge.is-premium .tariff-value {
  color: #f59e0b;
}

.admin-portal-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  transition: all 0.2s ease;
}

.admin-portal-link:hover {
  background: var(--accent);
  color: #000;
}

/* Red Danger Logout Button */
.profile-danger-logout-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 15px;
  border-radius: 10px;
  border: 1px solid rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.profile-danger-logout-btn:hover:not(:disabled) {
  background: #ef4444;
  color: #ffffff;
  border-color: #ef4444;
  box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3);
  transform: translateY(-1px);
}

.profile-danger-logout-btn:disabled {
  opacity: 0.55;
  cursor: wait;
}

/* Section Cards */
.profile-section-card {
  padding: 22px 24px;
  border-radius: 18px;
  border: 1px solid var(--panel-border);
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  backdrop-filter: blur(16px);
}

.profile-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.profile-section-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
  letter-spacing: -0.015em;
}

.favorite-heart-icon {
  color: #ef4444;
}

.profile-edit-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s ease;
}

.profile-edit-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* Fields Grid */
.profile-fields-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

.profile-field-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 12px;
  background: color-mix(in srgb, var(--control) 50%, transparent);
  border: 1px solid var(--panel-border);
}

.profile-field-box dt {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
  font-weight: 650;
  color: var(--muted);
  margin: 0;
}

.field-icon {
  font-size: 11px;
  color: var(--accent);
  opacity: 0.85;
}

.profile-field-box dd {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  word-break: break-word;
}

.profile-field-box dd.is-empty {
  color: var(--muted);
  font-weight: 400;
  opacity: 0.6;
}

/* Edit Form */
.profile-edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.profile-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 11px;
  font-weight: 650;
  color: var(--muted);
}

.form-field input {
  width: 100%;
  height: 38px;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--text);
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s ease;
}

.form-field input:focus {
  border-color: var(--accent);
}

.profile-form-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.cancel-btn {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}

.save-btn {
  padding: 7px 18px;
  border-radius: 8px;
  border: 0;
  background: var(--accent);
  color: #000;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
}

.save-btn:disabled {
  opacity: 0.55;
  cursor: wait;
}

/* Favorites */
.favorites-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.profile-favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}

.favorites-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 28px 16px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--control) 30%, transparent);
  border: 1px dashed var(--panel-border);
}

.favorites-empty-icon {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  font-size: 18px;
  margin-bottom: 10px;
}

.favorites-empty-state h3 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.favorites-empty-state p {
  margin: 0 0 14px;
  font-size: 12px;
  color: var(--muted);
  max-width: 300px;
  line-height: 1.4;
}

.favorites-explore-btn {
  font-size: 12px;
  font-weight: 700;
  padding: 7px 16px;
  border-radius: 8px;
  background: var(--accent);
  color: #000;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.favorites-loading-state {
  padding: 20px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

/* Responsive */
@media (max-width: 640px) {
  .profile-user-card {
    flex-direction: column;
    align-items: stretch;
  }

  .profile-user-actions {
    justify-content: space-between;
    padding-top: 12px;
    border-top: 1px solid var(--panel-border);
  }

  .profile-fields-grid,
  .profile-form-grid {
    grid-template-columns: 1fr;
  }

  .profile-favorites-grid {
    grid-template-columns: 1fr;
  }
}
</style>
