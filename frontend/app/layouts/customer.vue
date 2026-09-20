<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faCalendarCheck,
  faCrown,
  faHouse,
  faLock,
  faRightToBracket,
  faShieldHalved,
  faUser,
} from "@fortawesome/free-solid-svg-icons"
import TelegramAuthModal from "~/components/auth/TelegramAuthModal.vue"

const { locale, load: loadTranslations, t } = useTranslations()
const subscriptionState = useSubscription()
const auth = useAuth()
const showAuthModal = ref(false)

await loadTranslations()
if (["auth.login_tab", "profile.subscription_paid"].some(code => t(code) === code)) await loadTranslations(locale.value, true)
await auth.load().catch(() => null)
if (auth.isAuthenticated.value) {
  await subscriptionState.load().catch(() => null)
}

const subscriptionTitle = computed(() => {
  const value = subscriptionState.subscription.value
  if (!subscriptionState.isPaid.value || !value?.expires_at) return t("profile.no_subscription")
  const date = new Intl.DateTimeFormat(locale.value, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value.expires_at))
  return t("profile.subscription_active_until", { date })
})

const onAuthenticated = async () => {
  await auth.load(true)
  if (auth.isAuthenticated.value) {
    await subscriptionState.load(true).catch(() => null)
  }
}
</script>

<template>
  <div class="customer-shell">
    <header class="customer-header">
      <AppBrand />

      <nav class="customer-nav" :aria-label="t('nav.main')">
        <NuxtLink to="/" exact-active-class="active">
          <FontAwesomeIcon :icon="faHouse" />
          <span>{{ t("nav.home") }}</span>
        </NuxtLink>
        <NuxtLink v-if="auth.isAuthenticated.value" to="/bookings" exact-active-class="active">
          <FontAwesomeIcon :icon="faCalendarCheck" />
          <span>{{ t("bookings.my_bookings") }}</span>
        </NuxtLink>
        <NuxtLink
          v-if="auth.isAuthenticated.value && ['ADMIN', 'MODERATOR'].includes(auth.user.value?.role || '')"
          to="/admin"
          class="admin-portal-link"
        >
          <span>⚡ Admin</span>
        </NuxtLink>
      </nav>

      <div class="customer-actions">
        <span
          v-if="auth.isAuthenticated.value"
          class="subscription-chip"
          :class="{ paid: subscriptionState.isPaid.value }"
          :title="subscriptionTitle"
        >
          <FontAwesomeIcon :icon="subscriptionState.isPaid.value ? faCrown : faLock" />
          {{ t(subscriptionState.isPaid.value ? "profile.subscription_paid" : "profile.subscription_free") }}
        </span>

        <!-- Profile icon: opens Telegram Login modal if unauthenticated, or navigates to /profile if authenticated -->
        <button
          v-if="!auth.isAuthenticated.value"
          type="button"
          class="profile-trigger"
          :aria-label="t('auth.login_tab') || 'Kirish'"
          :title="t('auth.login_tab') || 'Kirish'"
          @click="showAuthModal = true"
        >
          <FontAwesomeIcon :icon="faUser" />
        </button>
        <NuxtLink
          v-else
          class="profile-trigger"
          to="/profile"
          :aria-label="t('nav.profile') || 'Profil'"
          :title="t('nav.profile') || 'Profil'"
        >
          <FontAwesomeIcon :icon="faUser" />
        </NuxtLink>
        <AppUiPreferences />
      </div>
    </header>

    <main class="customer-main">
      <slot />
    </main>

    <!-- Global Telegram Login Modal -->
    <TelegramAuthModal
      v-model="showAuthModal"
      @authenticated="onAuthenticated"
    />
  </div>
</template>

<style scoped>
.login-trigger-btn {
  border: 0;
  cursor: pointer;
  font: inherit;
}
</style>
