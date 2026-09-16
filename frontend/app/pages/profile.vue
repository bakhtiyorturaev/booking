<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faCalendar,
  faLocationDot,
  faPen,
  faPhone,
  faRightFromBracket,
  faCrown,
  faUser,
} from "@fortawesome/free-solid-svg-icons"

import { useAuthApi } from "~/api/auth"
import { useSubscriptionApi } from "~/api/subscription"
import { ApiRequestError } from "~/types/api"

definePageMeta({
  layout: "customer",
  middleware: "auth",
})

const auth = useAuth()
const authApi = useAuthApi()
const subscriptionApi = useSubscriptionApi()
const subscriptionState = useSubscription()
const { user } = auth
const { locale, load, t } = useTranslations()

await load()
const profileCodes = [
  "auth.phone_number", "auth.city", "auth.birth_date", "nav.logout", "common.free",
  "profile.personal_details", "common.edit", "common.save", "common.cancel", "common.currency_uzs",
  "bookings.subscription_required", "common.days_count", "profile.subscription_plans", "profile.buy_subscription", "profile.checkout_processing", "profile.payment_successful", "profile.payment_failed",
]
if (profileCodes.some(code => t(code) === code)) {
  await load(locale.value, true).catch(() => undefined)
}

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
      </article>
    </div>
  </section>
</template>

<style scoped>
@media (max-width: 640px) {
  .profile-grid {
    grid-template-columns: 1fr;
    gap: 16px;
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
