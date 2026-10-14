<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faBars,
  faCalendarCheck,
  faHouse,
  faRightToBracket,
  faShieldHalved,
  faUser,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"
import TelegramAuthModal from "~/components/auth/TelegramAuthModal.vue"

const { locale, load: loadTranslations, t } = useTranslations()
const auth = useAuth("customer")
const showAuthModal = ref(false)
const route = useRoute()
const menuOpen = ref(false)
const menuButton = ref<HTMLButtonElement | null>(null)
const closeMenu = () => {
  if (!menuOpen.value) return
  menuOpen.value = false
  void nextTick(() => menuButton.value?.focus())
}
watch(() => route.fullPath, () => { menuOpen.value = false })
const onKeydown = (event: KeyboardEvent) => { if (event.key === "Escape") closeMenu() }
onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
const isHome = computed(() => route.path === "/" || route.path === "/catalog")

await loadTranslations()
if (["auth.login_tab", "profile.subscription_paid"].some(code => t(code) === code)) await loadTranslations(locale.value, true)
await auth.load().catch(() => null)
const favorites = useFavorites()
onMounted(() => { void favorites.load().catch(() => null) })
watch(() => auth.user.value?.id, () => { void favorites.load(true).catch(() => null) })
const onAuthenticated = async () => {
  await auth.load(true)

}
</script>

<template>
  <div class="customer-shell" :class="{ 'customer-shell--home': isHome }">
    <header class="customer-header">
      <div class="customer-header-start">
        <button
          ref="menuButton"
          type="button"
          class="customer-menu-button"
          aria-controls="customer-drawer"
          :aria-expanded="menuOpen"
          :aria-label="t('nav.menu') || 'Menyu'"
          @click="menuOpen = !menuOpen"
        >
          <FontAwesomeIcon :icon="faBars" />
        </button>
        <AppBrand />
      </div>

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

    <!-- Yon panel: kategoriyalar (hamburger orqali ochiladi) -->
    <div v-show="menuOpen" class="customer-drawer-backdrop" @click="closeMenu" />
    <aside id="customer-drawer" class="customer-drawer" :class="{ open: menuOpen }" :aria-hidden="!menuOpen" :inert="!menuOpen" :aria-label="t('nav.menu') || 'Menyu'">
      <div class="customer-drawer-head">
        <strong>{{ t("nav.menu") || "Menyu" }}</strong>
        <button type="button" class="customer-menu-button" :aria-label="t('common.close') || 'Yopish'" @click="closeMenu">
          <FontAwesomeIcon :icon="faXmark" />
        </button>
      </div>
      <NuxtLink to="/" exact-active-class="active" class="customer-drawer-home" @click="closeMenu">
        <FontAwesomeIcon :icon="faHouse" />
        <span>{{ t("nav.home") }}</span>
      </NuxtLink>
      <AppCategoryNav @navigate="closeMenu" />
    </aside>

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
