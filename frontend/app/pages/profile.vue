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
  faUser,
} from "@fortawesome/free-solid-svg-icons"

import { useAuthApi } from "~/api/auth"
import { useSubscriptionApi } from "~/api/subscription"
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
const subscriptionApi = useSubscriptionApi()
const subscriptionState = useSubscription()
const favorites = useFavorites()
const { user } = auth
const { locale, load, t } = useTranslations()

await load()
await favorites.load(true).catch(() => null)
const profileCodes = [
  "auth.phone_number", "auth.city", "auth.birth_date", "nav.logout", "common.free",
  "profile.personal_details", "common.edit", "common.save", "common.cancel", "common.currency_uzs",
  "bookings.subscription_required", "common.days_count", "profile.subscription_plans", "profile.buy_subscription", "profile.checkout_processing", "profile.payment_successful", "profile.payment_failed",
]
if (profileCodes.some(code => t(code) === code)) {
  await load(locale.value, true).catch(() => undefined)
}

useHead({
  title: computed(() => t("profile.title") || "Mening profilim"),
})

const editing = ref(false)
const pending = ref(false)
const logoutPending = ref(false)
const checkoutPending = ref("")
const checkoutMessage = ref("")
const { data: plans } = await useAsyncData(
  "subscription-plans",
  () => subscriptionApi.plans(),
  { default: () => [] },
)
await subscriptionState.load()
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
  return user.value?.phone || fullName.value || user.value?.username || ""
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

const formatPrice = (value: number) =>
  `${new Intl.NumberFormat(locale.value).format(value / 100)} ${t("common.currency_uzs")}`

const startCheckout = async (planCode: string) => {
  if (checkoutPending.value) return
  checkoutPending.value = planCode
  checkoutMessage.value = ""
  const toast = useToast()
  try {
    const payment = await subscriptionApi.checkout(planCode, crypto.randomUUID())
    if (payment.checkout_url) {
      await navigateTo(payment.checkout_url, { external: true })
      return
    }
    await subscriptionState.load(true)
    const successMsg = t("profile.payment_successful")
    checkoutMessage.value = successMsg
    toast.success(successMsg)
  } catch (error) {
    const errText = error instanceof ApiRequestError ? error.message : t("common.backend_unavailable")
    checkoutMessage.value = errText
    toast.error(errText)
  } finally {
    checkoutPending.value = ""
  }
}

const formatDate = (value?: string | null) => {
  if (!value) return t("common.free")
  return new Intl.DateTimeFormat(locale.value, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(value))
}

const fields = computed(() => [
  { code: "auth.phone_number", value: user.value?.phone, icon: faPhone },
  { code: "auth.city", value: profile.value?.city, icon: faLocationDot },
  { code: "auth.birth_date", value: formatDate(profile.value?.birth_date), icon: faCalendar },
])

const favoriteBranches = computed(() => {
  const list: BranchListSummary[] = []
  for (const item of favorites.favoritesList.value) {
    if (item.club?.branches?.length) {
      for (const branch of item.club.branches) {
        list.push({
          ...branch,
          club: {
            id: item.club.id,
            name: item.club.name,
            category: item.club.category,
            category_display: item.club.category_display,
            slug: item.club.slug,
            logo: item.club.logo,
            rating: item.club.rating,
            review_count: item.club.review_count,
          },
          is_favorite: true,
        })
      }
    } else if (item.club) {
      list.push({
        id: item.club.id,
        name: item.club.name,
        address: "",
        full_address: "",
        city: { id: "", name: "", slug: "" },
        district: null,
        latitude: "0",
        longitude: "0",
        is_24_hours: false,
        service_types: item.club.service_types || [],
        min_price_tiyin: item.club.min_price_tiyin,
        cover_image: item.club.cover || item.club.logo,
        distance_km: item.club.distance_km,
        is_favorite: true,
        club: {
          id: item.club.id,
          name: item.club.name,
          category: item.club.category,
          category_display: item.club.category_display,
          slug: item.club.slug,
          logo: item.club.logo,
          rating: item.club.rating,
          review_count: item.club.review_count,
        },
      })
    }
  }
  return list
})
</script>

<template>
  <section class="profile-page">
    <div class="profile-layout">
      <aside class="profile-summary-card">
        <div class="profile-avatar-large">
          <img v-if="profile?.avatar_url" :src="profile.avatar_url" :alt="displayName">
          <FontAwesomeIcon v-else :icon="faUser" />
        </div>
        <div class="profile-identity">
          <h1>{{ displayName }}</h1>
          <p v-if="accountDetail">{{ accountDetail }}</p>
        </div>
        <NuxtLink
          v-if="['ADMIN', 'MODERATOR'].includes(user?.role || '')"
          to="/admin"
          class="primary-button admin-entry-btn"
        >
          ⚡ {{ t("admin.dashboard") }}
        </NuxtLink>
        <button
          type="button"
          class="signout-button"
          :disabled="logoutPending"
          @click="signOut"
        >
          <FontAwesomeIcon :icon="faRightFromBracket" />
          {{ logoutPending ? t("common.loading") : t("nav.logout") }}
        </button>
      </aside>

      <article class="profile-details-card">
        <header class="profile-card-heading">
          <h2>{{ t("profile.personal_details") }}</h2>
          <button v-if="!editing" type="button" @click="startEditing">
            <FontAwesomeIcon :icon="faPen" />
            {{ t("common.edit") }}
          </button>
        </header>

        <form v-if="editing" class="profile-edit-form" @submit.prevent="saveProfile">
          <div class="profile-form-grid">
            <label class="form-field">
              <span class="field-label">{{ t("auth.full_name") }}</span>
              <input v-model="form.full_name" type="text">
            </label>
            <label class="form-field">
              <span class="field-label">{{ t("auth.city") }}</span>
              <input v-model="form.city" type="text">
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
            <button type="button" class="secondary-button" @click="cancelEditing">
              {{ t("common.cancel") }}
            </button>
            <button type="submit" class="primary-button" :disabled="pending">
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
          <dl class="profile-fields">
            <div v-for="field in fields" :key="field.code">
              <dt>
                <FontAwesomeIcon :icon="field.icon" />
                {{ t(field.code) }}
              </dt>
              <dd>{{ field.value || t("common.free") }}</dd>
            </div>
          </dl>
        </template>

        <section class="profile-subscription-section">
          <div class="profile-card-heading">
            <h2><FontAwesomeIcon :icon="faCrown" /> {{ t("profile.subscription") }}</h2>
            <span class="subscription-chip" :class="{ paid: subscriptionState.isPaid.value }">
              {{ subscriptionState.isPaid.value ? t("profile.subscription_paid") : t("profile.subscription_free") }}
            </span>
          </div>
          <p v-if="subscriptionState.isPaid.value" class="subscription-current-status">
            {{ t("profile.subscription_active_until", { date: formatDate(subscriptionState.subscription.value?.expires_at) }) }}
          </p>
          <p v-else class="subscription-current-status">{{ t("bookings.subscription_required") }}</p>
          <p v-if="checkoutMessage" class="form-message profile-form-message" role="status">
            {{ checkoutMessage }}
          </p>
          <div v-if="plans.length" class="subscription-plan-list">
            <article v-for="plan in plans" :key="plan.code" class="subscription-plan-card">
              <div>
                <strong>{{ plan.name }}</strong>
                <span>{{ t("common.days_count", { days: plan.duration_days }) }}</span>
              </div>
              <div>
                <strong>{{ formatPrice(plan.price_tiyin) }}</strong>
                <button type="button" :disabled="Boolean(checkoutPending)" @click="startCheckout(plan.code)">
                  {{ checkoutPending === plan.code ? t("profile.checkout_processing") : t("profile.buy_subscription") }}
                </button>
              </div>
            </article>
          </div>
          <p v-else class="subscription-current-status">{{ t("profile.subscription_plans") }}</p>
        </section>

        <!-- Favorites Section -->
        <section class="profile-favorites-section">
          <div class="profile-card-heading">
            <h2>
              <FontAwesomeIcon :icon="faHeart" class="favorite-heart-icon" />
              {{ t("profile.favorites") }}
              <span v-if="favoriteBranches.length" class="favorites-count-badge">
                {{ favoriteBranches.length }}
              </span>
            </h2>
          </div>

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
            <NuxtLink to="/" class="primary-button favorites-explore-btn">
              {{ t("profile.explore_clubs") }}
            </NuxtLink>
          </div>
        </section>
      </article>
    </div>
  </section>
</template>

<style scoped>
.profile-favorites-section {
  margin-top: 26px;
  padding-top: 24px;
  border-top: 1px solid var(--panel-border);
}

.profile-favorites-section h2 {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.02em;
}

.favorite-heart-icon {
  color: #ef4444;
}

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
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.favorites-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 36px 16px;
  margin-top: 16px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--control) 40%, transparent);
  border: 1px dashed var(--panel-border);
}

.favorites-empty-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  font-size: 20px;
  margin-bottom: 12px;
}

.favorites-empty-state h3 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.favorites-empty-state p {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--muted);
  max-width: 320px;
  line-height: 1.4;
}

.favorites-explore-btn {
  font-size: 13px;
  font-weight: 700;
  padding: 8px 18px;
  border-radius: 9px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.favorites-loading-state {
  padding: 24px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 640px) {
  .profile-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .profile-favorites-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .subscription-plan-card {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .subscription-plan-card > div:last-child {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .subscription-plan-card button {
    flex: 1;
  }
}
</style>
