<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faBars,
  faCalendarCheck,
  faHouse,
  faPaperPlane,
  faShieldHalved,
  faTableCellsLarge,
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
  <!-- Shahar manzarasi foni barcha mijoz sahifalarida (filial, sartarosh, bron va h.k.) bir xil. -->
  <div class="customer-shell customer-shell--home">
    <header class="customer-header glass-panel">
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
        <NuxtLink to="/" exact-active-class="active">{{ t("nav.home") || "Asosiy" }}</NuxtLink>
        <NuxtLink to="/catalog" active-class="active">Katalog</NuxtLink>
        <NuxtLink to="/#xarita">Xarita</NuxtLink>
        <NuxtLink v-if="auth.isAuthenticated.value" to="/bookings" active-class="active">{{ t("bookings.my_bookings") }}</NuxtLink>
        <button v-else type="button" class="customer-nav-button" @click="showAuthModal = true">{{ t("bookings.my_bookings") }}</button>
        <NuxtLink
          v-if="auth.isAuthenticated.value && ['ADMIN', 'MODERATOR'].includes(auth.user.value?.role || '')"
          to="/cabinet"
          class="admin-portal-link"
        >
          <FontAwesomeIcon :icon="faShieldHalved" aria-hidden="true" /><span>Admin</span>
        </NuxtLink>
      </nav>

      <div class="customer-actions">
        <AppUiPreferences />
        <NuxtLink
          v-if="auth.isAuthenticated.value"
          class="profile-trigger"
          to="/profile"
          :aria-label="t('nav.profile') || 'Profil'"
          :title="t('nav.profile') || 'Profil'"
        >
          <FontAwesomeIcon :icon="faUser" />
        </NuxtLink>
        <button v-else type="button" class="header-login" @click="showAuthModal = true">
          <FontAwesomeIcon :icon="faPaperPlane" aria-hidden="true" />
          <span>Telegram bilan kirish</span>
        </button>
      </div>
    </header>

    <aside class="customer-desktop-sidebar" :aria-label="t('nav.menu') || 'Menyu'">
      <NuxtLink to="/" exact-active-class="active" class="customer-drawer-home">
        <FontAwesomeIcon :icon="faHouse" />
        <span>{{ t("nav.home") }}</span>
      </NuxtLink>
      <AppCategoryNav />
    </aside>

    <!-- Mobile service drawer -->
    <div v-show="menuOpen" class="customer-drawer-backdrop" @click="closeMenu" />
    <aside id="customer-drawer" class="customer-drawer" :class="{ open: menuOpen }" :aria-hidden="!menuOpen" :inert="!menuOpen" :aria-label="t('nav.menu') || 'Menyu'">
      <div class="customer-drawer-head">
        <strong>{{ t("nav.menu") || "Menyu" }}</strong>
        <button type="button" class="customer-menu-button" :aria-label="t('common.close') || 'Yopish'" @click="closeMenu">
          <FontAwesomeIcon :icon="faXmark" />
        </button>
      </div>
      <NuxtLink v-if="auth.isAuthenticated.value" to="/bookings" exact-active-class="active" class="customer-drawer-home customer-bookings-link" @click="closeMenu">
        <FontAwesomeIcon :icon="faCalendarCheck" />
        <span>{{ t("bookings.my_bookings") }}</span>
      </NuxtLink>
      <NuxtLink to="/" exact-active-class="active" class="customer-drawer-home" @click="closeMenu">
        <FontAwesomeIcon :icon="faHouse" />
        <span>{{ t("nav.home") }}</span>
      </NuxtLink>
      <AppCategoryNav v-if="menuOpen" @navigate="closeMenu" />
    </aside>

    <main class="customer-main">
      <slot />
    </main>

    <!-- Telefonda pastki suzuvchi menyu (ilovalardagidek). -->
    <nav class="bottom-nav" :aria-label="t('nav.main') || 'Asosiy menyu'">
      <NuxtLink to="/" exact-active-class="active">
        <FontAwesomeIcon :icon="faHouse" aria-hidden="true" /><span>{{ t("nav.home") || "Asosiy" }}</span>
      </NuxtLink>
      <NuxtLink to="/catalog" active-class="active">
        <FontAwesomeIcon :icon="faTableCellsLarge" aria-hidden="true" /><span>Katalog</span>
      </NuxtLink>
      <NuxtLink v-if="auth.isAuthenticated.value" to="/bookings" active-class="active">
        <FontAwesomeIcon :icon="faCalendarCheck" aria-hidden="true" /><span>Bronlar</span>
      </NuxtLink>
      <button v-else type="button" @click="showAuthModal = true">
        <FontAwesomeIcon :icon="faCalendarCheck" aria-hidden="true" /><span>Bronlar</span>
      </button>
      <NuxtLink v-if="auth.isAuthenticated.value" to="/profile" active-class="active">
        <FontAwesomeIcon :icon="faUser" aria-hidden="true" /><span>{{ t("nav.profile") || "Profil" }}</span>
      </NuxtLink>
      <button v-else type="button" @click="showAuthModal = true">
        <FontAwesomeIcon :icon="faUser" aria-hidden="true" /><span>{{ t("auth.login_tab") || "Kirish" }}</span>
      </button>
    </nav>

    <!-- Global Telegram Login Modal -->
    <TelegramAuthModal
      v-model="showAuthModal"
      @authenticated="onAuthenticated"
    />
  </div>
</template>

<style scoped>
.bottom-nav { display: none; }
@media (max-width: 900px) {
  .bottom-nav {
    position: fixed;
    left: 12px;
    right: 12px;
    bottom: calc(12px + env(safe-area-inset-bottom, 0px));
    z-index: 30;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    padding: 6px;
    border: 1px solid var(--glass-border);
    border-radius: 24px;
    background: color-mix(in srgb, var(--surface) 82%, transparent);
    -webkit-backdrop-filter: blur(18px) saturate(160%);
    backdrop-filter: blur(18px) saturate(160%);
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
  }
  .bottom-nav a, .bottom-nav button {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    min-height: 52px;
    padding: 0;
    border: 0;
    border-radius: 18px;
    background: none;
    color: var(--muted);
    font: inherit;
    font-size: 12px;
    font-weight: 700;
    text-decoration: none;
    cursor: pointer;
  }
  .bottom-nav svg { font-size: 19px; }
  .bottom-nav .active { background: var(--cta); color: #fff; box-shadow: var(--cta-glow); }
  .bottom-nav a:focus-visible, .bottom-nav button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  /* Menyu kontentni yopib qo'ymasin. */
  .customer-main { padding-bottom: calc(96px + env(safe-area-inset-bottom, 0px)) !important; }
}
.customer-bookings-link {
  min-height: 48px;
  margin-bottom: 6px;
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent);
}

.login-trigger-btn {
  border: 0;
  cursor: pointer;
  font: inherit;
}
</style>
