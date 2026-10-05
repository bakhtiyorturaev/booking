<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faCalendarCheck,
  faHouse,
  faRightToBracket,
  faShieldHalved,
  faUser,
} from "@fortawesome/free-solid-svg-icons"
import TelegramAuthModal from "~/components/auth/TelegramAuthModal.vue"

const { locale, load: loadTranslations, t } = useTranslations()
const auth = useAuth("customer")
const showAuthModal = ref(false)

await loadTranslations()
if (["auth.login_tab", "profile.subscription_paid"].some(code => t(code) === code)) await loadTranslations(locale.value, true)
await auth.load().catch(() => null)
const onAuthenticated = async () => {
  await auth.load(true)

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
          to="/cabinet"
          class="admin-portal-link"
        >
          <span>⚡ Admin</span>
        </NuxtLink>
      </nav>

      <div class="customer-actions">
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
