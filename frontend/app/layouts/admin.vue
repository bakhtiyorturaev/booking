<script setup lang="ts">
import VenueBillingBadge from "~/components/cabinet/VenueBillingBadge.vue"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faBolt, faBorderAll, faBuilding, faCodeBranch, faScissors, faCalendarCheck, faCreditCard, faUsers, faArrowUpRightFromSquare, faBars, faXmark, faSun, faMoon, faKey, faArrowRightFromBracket, faChevronRight, faShieldHalved } from "@fortawesome/free-solid-svg-icons"
import ChangePasswordModal from "~/components/auth/ChangePasswordModal.vue"
import { useAuth } from "~/composables/useAuth"
import { useTheme } from "~/composables/useTheme"
import { useAdminApi } from "~/api/admin"
import { billingAlertLevel } from "~/composables/useVenueBillingStatus"
import type { BillingVenue } from "~/types/venueBilling"

const cabinetPath = useCabinetPath()
const { user, logout } = useAuth()
const { mode: theme, toggle: toggleTheme } = useTheme()
const route = useRoute()
const isSidebarOpen = ref(false)
const showChangePasswordModal = ref(false)
const isLoggingOut = ref(false)
const showProfileMenu = ref(false)
const profileMenu = ref<HTMLElement | null>(null)
const closeProfileMenu = (event: MouseEvent) => { if (!profileMenu.value?.contains(event.target as Node)) showProfileMenu.value = false }
onMounted(() => document.addEventListener("click", closeProfileMenu))
onBeforeUnmount(() => document.removeEventListener("click", closeProfileMenu))
watch(() => route.fullPath, () => { showProfileMenu.value = false })
const sidebar = ref<HTMLElement | null>(null)
const menuButton = ref<HTMLButtonElement | null>(null)
const roleLabel = computed(() => ({ ADMIN: "Administrator", MODERATOR: "Moderator", CLIENT: "Muassasa egasi" })[user.value?.role || ""] || (user.value?.has_barber_profile ? "Sartarosh" : user.value?.has_owned_clubs ? "Muassasa egasi" : "Xodim"))
const displayName = computed(() => user.value?.full_name || user.value?.profile?.full_name || user.value?.username || "Xodim")
const isStaff = computed(() => user.value?.is_staff || user.value?.is_superuser || ["ADMIN", "MODERATOR"].includes(user.value?.role || ""))
const billingClock = useState<number>("venue-billing-clock", () => Date.now())
const clientVenues = ref<(BillingVenue & { destination: string })[]>([])
const billingStatuses = useCabinetBillingCache()
const billingNotices = computed(() => clientVenues.value.filter(venue => billingAlertLevel(venue, billingClock.value) !== "NONE"))
const billingApi = useAdminApi()
let billingTimer: ReturnType<typeof setInterval> | undefined
let billingLoadVersion = 0
const refreshClientBilling = async () => {
  const ownerId = user.value?.id
  const version = ++billingLoadVersion
  if (isStaff.value || !ownerId) { clientVenues.value = []; billingStatuses.value = {}; return }
  const allBillingPages = async (fetcher: (params: Record<string, string | number>) => Promise<{ results: BillingVenue[]; next: string | null }>) => {
    const items: BillingVenue[] = []
    let page = 1
    let hasNext = true
    while (hasNext) {
      if (version !== billingLoadVersion || user.value?.id !== ownerId) return []
      const response = await fetcher({ page: page++, page_size: 100 })
      items.push(...response.results)
      hasNext = Boolean(response.next)
    }
    return items
  }
  try {
    const [clubs, branches, barbers] = await Promise.all([
      allBillingPages(billingApi.getVenueBilling),
      allBillingPages(billingApi.getBranchBilling),
      allBillingPages(billingApi.getBarberBilling),
    ])
    if (version === billingLoadVersion && user.value?.id === ownerId && !isStaff.value) {
      clientVenues.value = [
        ...branches.map(venue => ({ ...venue, name: `${venue.club_name} — ${venue.name}`, destination: '/branches' })),
        ...barbers.map(venue => ({ ...venue, destination: '/barbers' })),
      ]
      billingStatuses.value = Object.fromEntries(clubs.map(venue => [venue.id, venue]))
    }
  } catch { /* Billing badges remain available on the venue pages. */ }
}

onMounted(() => {
  billingClock.value = Date.now()
  void refreshClientBilling()
  billingTimer = setInterval(() => { billingClock.value = Date.now(); void refreshClientBilling() }, 60000)
})
watch(() => user.value?.id, () => { clientVenues.value = []; billingStatuses.value = {}; void refreshClientBilling() })
onBeforeUnmount(() => { if (billingTimer) clearInterval(billingTimer) })
const navGroups = computed(() => [
  { label: "Ish maydoni", items: [
    { to: cabinetPath(''), label: "Umumiy ko‘rinish", icon: faBorderAll, exact: true },
    { to: cabinetPath('/bookings'), label: "Bronlar", icon: faCalendarCheck },
    { to: cabinetPath('/payments'), label: "To‘lovlar", icon: faCreditCard },
  ] },
  { label: "Boshqaruv", items: [
    { to: cabinetPath('/clubs'), label: "Muassasalar", icon: faBuilding },
    { to: cabinetPath('/branches'), label: "Filiallar va zonalar", icon: faCodeBranch },
    { to: cabinetPath('/barbers'), label: "Sartaroshlar", icon: faScissors },
    { to: cabinetPath('/users'), label: "Mijozlar", icon: faUsers },
  ] },
].map(group => ({ ...group, items: group.items.filter(item => isStaff.value || ![cabinetPath(''), cabinetPath('/users'), cabinetPath('/payments')].includes(item.to)) })))
const isActive = (item: { to: string; exact?: boolean }) => item.exact ? route.path === item.to : route.path.startsWith(`${item.to}/`) || route.path === item.to
const clientsMenuOpen = ref(route.path.includes('/users'))
watch(() => route.path, path => { if (path.includes('/users')) clientsMenuOpen.value = true })
const currentPage = computed(() => route.path.endsWith('/users/customers') ? 'Foydalanuvchilar' : route.path.endsWith('/users/clients') ? 'Clientlar' : navGroups.value.flatMap(group => group.items).find(isActive)?.label || "Kabinet")
const closeSidebar = () => {
  isSidebarOpen.value = false
  menuButton.value?.focus()
}
const onSidebarKeydown = (event: KeyboardEvent) => {
  if (!isSidebarOpen.value) return
  if (event.key === "Escape") closeSidebar()
  if (event.key !== "Tab") return
  const items = sidebar.value?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')
  if (!items?.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
let previousOverflow = ""
watch(isSidebarOpen, async (open) => {
  if (!import.meta.client) return
  if (open) {
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    await nextTick()
    sidebar.value?.querySelector<HTMLElement>(".sidebar-close")?.focus()
  } else document.body.style.overflow = previousOverflow
})
watch(() => route.fullPath, () => { isSidebarOpen.value = false })
const onResize = () => { if (window.innerWidth >= 1024) isSidebarOpen.value = false }
onMounted(() => window.addEventListener("resize", onResize))
onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize)
  if (isSidebarOpen.value) document.body.style.overflow = previousOverflow
})
const handleLogout = async () => {
  if (isLoggingOut.value) return
  isLoggingOut.value = true
  const loginPath = route.path.startsWith("/site/client/") ? "/site/client/login" : "/site/staff/login"
  try { await logout(); await navigateTo(loginPath) }
  catch { useToast().error("Chiqib bo‘lmadi. Qayta urinib ko‘ring.") }
  finally { isLoggingOut.value = false }
}
</script>

<template>
  <div class="cabinet-shell" :class="{ 'cabinet-dark': theme === 'dark' }">
    <a href="#cabinet-content" class="cabinet-skip">Asosiy sahifaga o‘tish</a>
    <div v-if="isSidebarOpen" class="cabinet-overlay" aria-hidden="true" @click="closeSidebar" />
    <aside id="cabinet-navigation" ref="sidebar" class="cabinet-sidebar" :class="{ 'is-open': isSidebarOpen }" :role="isSidebarOpen ? 'dialog' : undefined" :aria-modal="isSidebarOpen ? true : undefined" aria-label="Kabinet menyusi" @keydown="onSidebarKeydown">
      <div class="cabinet-brand-row">
        <NuxtLink :to="cabinetPath('')" class="cabinet-brand" aria-label="RezervUZ boshqaruv paneli">
          <span class="cabinet-logo"><FontAwesomeIcon :icon="faBolt" /></span>
          <span>Rezerv<span class="cabinet-brand-accent">UZ</span><small>Boshqaruv</small></span>
        </NuxtLink>
        <button type="button" class="cabinet-icon-button sidebar-close" aria-label="Menyuni yopish" @click="closeSidebar"><FontAwesomeIcon :icon="faXmark" /></button>
      </div>
      <div class="cabinet-workspace"><span class="workspace-mark"><FontAwesomeIcon :icon="faBuilding" /></span><div><strong>RezervUZ</strong><span>{{ isStaff ? "Xodimlar kabineti" : "Muassasa kabineti" }}</span></div><FontAwesomeIcon :icon="faShieldHalved" class="workspace-shield" /></div>
      <nav class="cabinet-nav" aria-label="Asosiy navigatsiya">
        <div v-for="group in navGroups" :key="group.label" class="cabinet-nav-group">
          <p class="cabinet-nav-label">{{ group.label }}</p>
          <template v-for="item in group.items" :key="item.to">
            <template v-if="item.to === cabinetPath('/users')">
              <button type="button" class="cabinet-nav-link clients-menu-toggle" :class="{ 'is-active': isActive(item) }" :aria-expanded="clientsMenuOpen" aria-controls="clients-submenu" @click="clientsMenuOpen = !clientsMenuOpen">
                <FontAwesomeIcon :icon="item.icon" /><span>{{ item.label }}</span><FontAwesomeIcon :icon="faChevronRight" class="nav-arrow" :class="{ 'submenu-open': clientsMenuOpen }" />
              </button>
              <div v-if="clientsMenuOpen" id="clients-submenu" class="cabinet-subnav">
                <NuxtLink :to="cabinetPath('/users/customers')" :aria-current="route.path.endsWith('/users/customers') ? 'page' : undefined">Foydalanuvchilar</NuxtLink>
                <NuxtLink :to="cabinetPath('/users/clients')" :aria-current="route.path.endsWith('/users/clients') ? 'page' : undefined">Clientlar</NuxtLink>
              </div>
            </template>
            <NuxtLink v-else :to="item.to" class="cabinet-nav-link" :class="{ 'is-active': isActive(item) }" :aria-current="isActive(item) ? 'page' : undefined">
              <FontAwesomeIcon :icon="item.icon" /><span>{{ item.label }}</span><FontAwesomeIcon v-if="isActive(item)" :icon="faChevronRight" class="nav-arrow" />
            </NuxtLink>
          </template>
        </div>
      </nav>
      <div class="cabinet-sidebar-bottom">
        <NuxtLink to="/" class="cabinet-site-link"><FontAwesomeIcon :icon="faArrowUpRightFromSquare" /><span>Saytni ochish</span></NuxtLink>
        <div class="cabinet-sidebar-user"><span class="cabinet-avatar">{{ displayName.slice(0, 1).toUpperCase() }}</span><div><strong>{{ displayName }}</strong><span>{{ roleLabel }}</span></div></div>
      </div>
    </aside>
    <div class="cabinet-workarea" :inert="isSidebarOpen || undefined">
      <header class="cabinet-topbar">
        <div class="cabinet-breadcrumb"><button ref="menuButton" type="button" class="cabinet-icon-button cabinet-menu-button" aria-label="Menyuni ochish" aria-controls="cabinet-navigation" :aria-expanded="isSidebarOpen" @click="isSidebarOpen = true"><FontAwesomeIcon :icon="faBars" /></button><span class="breadcrumb-root">Kabinet</span><span class="breadcrumb-divider"><FontAwesomeIcon :icon="faChevronRight" /></span><span class="breadcrumb-current">{{ currentPage }}</span></div>
        <div class="cabinet-topbar-actions">
          <button type="button" class="cabinet-icon-button" :aria-label="theme === 'dark' ? 'Yorug‘ rejim' : 'Qorong‘i rejim'" :title="theme === 'dark' ? 'Yorug‘ rejim' : 'Qorong‘i rejim'" @click="toggleTheme"><FontAwesomeIcon :icon="theme === 'dark' ? faSun : faMoon" /></button>
          <div ref="profileMenu" class="profile-menu" @keydown.esc="showProfileMenu = false" @focusout="event => { if (!profileMenu?.contains(event.relatedTarget as Node)) showProfileMenu = false }">
            <button type="button" class="cabinet-avatar profile-trigger" aria-label="Profil" :aria-expanded="showProfileMenu" aria-controls="profile-actions" @click="showProfileMenu = !showProfileMenu">{{ displayName.slice(0, 1).toUpperCase() }}</button>
            <div v-if="showProfileMenu" id="profile-actions" class="profile-actions">
              <strong>{{ displayName }}</strong><small>{{ roleLabel }}</small>
              <button type="button" @click="showProfileMenu = false; showChangePasswordModal = true"><FontAwesomeIcon :icon="faKey" />Parolni yangilash</button>
              <button type="button" :disabled="isLoggingOut" @click="showProfileMenu = false; handleLogout()"><FontAwesomeIcon :icon="faArrowRightFromBracket" />Chiqish</button>
            </div>
          </div>
        </div>
      </header>
      <div v-if="user?.password_expired" class="cabinet-password-notice"><FontAwesomeIcon :icon="faShieldHalved" /><span>Parolingizni yangilang.</span><button type="button" @click="showChangePasswordModal = true">Yangilash</button></div>
      <div v-if="!isStaff && billingNotices.length" class="billing-notices" aria-live="polite">
        <NuxtLink v-for="venue in billingNotices" :key="venue.id" :to="cabinetPath(venue.destination)" class="billing-notice" :class="billingAlertLevel(venue, billingClock).toLowerCase()"><span><strong>{{ venue.name }}</strong><small>To‘lov muddati</small></span><VenueBillingBadge :billing="venue" /></NuxtLink>
      </div>
      <main id="cabinet-content" class="cabinet-main" tabindex="-1"><slot /></main>
      <footer class="cabinet-footer"><span>RezervUZ</span><span>{{ roleLabel }}</span></footer>
    </div>
    <ChangePasswordModal v-model="showChangePasswordModal" :force="Boolean(user?.password_expired)" title="Parolni yangilash" @success="showChangePasswordModal = false" />
  </div>
</template>

<style scoped>
.clients-menu-toggle { width: calc(100% - 6px); border: 0; background: transparent; text-align: left; cursor: pointer; font-family: inherit; }
.submenu-open { transform: rotate(90deg); }
.cabinet-subnav { display: grid; gap: 2px; margin: 0 0 8px 24px; padding-left: 18px; border-left: 1px solid var(--panel-border); }
.cabinet-subnav a { display: flex; align-items: center; min-height: 44px; padding: 8px 12px; border-radius: 8px; font-size: 12px; color: var(--muted); text-decoration: none; }
.cabinet-subnav a:hover, .cabinet-subnav a[aria-current="page"] { color: var(--accent); background: var(--accent-soft); }

.profile-menu { position: relative; }
.profile-trigger { border: 0; cursor: pointer; min-width: 44px; min-height: 44px; }
.profile-actions { position: absolute; z-index: 90; top: calc(100% + 12px); right: 0; width: min(260px, calc(100vw - 32px)); background: var(--surface); border: 1px solid var(--panel-border); border-radius: 12px; box-shadow: 0 12px 36px #0002; padding: 12px; }
.profile-actions strong, .profile-actions small { display: block; padding: 4px 8px; overflow-wrap: anywhere; }
.profile-actions small { color: var(--muted); margin-bottom: 8px; }
.profile-actions button { width: 100%; display: flex; align-items: center; gap: 12px; min-height: 44px; padding: 10px 8px; background: transparent; color: var(--text); border: 0; border-radius: 8px; cursor: pointer; text-align: left; }
.profile-actions button:hover { background: var(--control); }

.billing-notices { display: grid; gap: 10px; padding: 20px 32px 0; }
.billing-notice { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 18px; border-radius: 10px; border: 1px solid currentColor; text-decoration: none; color: var(--warning); background: var(--warning-soft); }
.billing-notice:is(.critical, .expired) { color: var(--danger); background: var(--danger-soft); }
.billing-notice > span { min-width: 0; }
.billing-notice > span strong { display: block; font-size: 13px; overflow-wrap: anywhere; }
.billing-notice > span small { display: block; margin-top: 5px; font-size: 11px; }
@media (max-width: 700px) { .billing-notices { padding: 16px 16px 0; } .billing-notice { padding: 12px; gap: 10px; flex-wrap: wrap; } }
.cabinet-shell { display: flex; min-height: 100dvh; color: var(--text); background: var(--page); }
.cabinet-sidebar { position: fixed; inset: 0 auto 0 0; width: 248px; display: flex; flex-direction: column; background: var(--surface); border-right: 1px solid var(--panel-border); z-index: 70; }
.cabinet-brand-row { display: flex; align-items: center; justify-content: space-between; height: 88px; padding: 20px 24px; }
.cabinet-brand { display: flex; align-items: center; gap: 11px; font-size: 22px; font-weight: 750; letter-spacing: -.7px; color: var(--text); text-decoration: none; }
.cabinet-logo { display: grid; place-items: center; width: 36px; height: 40px; border-radius: 11px; background: var(--accent); color: white; font-size: 17px; }
.cabinet-brand-accent { color: var(--accent); }
.cabinet-brand small { display: block; font-size: 10px; letter-spacing: 1.8px; text-transform: uppercase; margin-top: 2px; color: var(--muted); font-weight: 600; }
.cabinet-workspace { display: flex; align-items: center; gap: 10px; padding: 13px 12px; margin: 8px 16px 20px; background: var(--control); border: 1px solid var(--panel-border); border-radius: 10px; }
.workspace-mark { display: grid; place-items: center; width: 32px; height: 32px; background: var(--surface); border: 1px solid var(--panel-border); border-radius: 8px; color: var(--muted); font-size: 13px; }
.cabinet-workspace strong, .cabinet-sidebar-user strong { display: block; font-size: 13px; font-weight: 650; }
.cabinet-workspace div > span, .cabinet-sidebar-user div > span { display: block; color: var(--muted); font-size: 11px; margin-top: 3px; }
.workspace-shield { margin-left: auto; color: var(--muted); font-size: 12px; }
.cabinet-nav { flex: 1; overflow-y: auto; padding: 0 14px; }
.cabinet-nav-group + .cabinet-nav-group { margin-top: 27px; }
.cabinet-nav-label { margin: 0 12px 9px; font-size: 10px; font-weight: 650; letter-spacing: 1.3px; text-transform: uppercase; color: var(--muted); }
.cabinet-nav-link { display: flex; align-items: center; gap: 12px; padding: 12px; margin: 3px 0; border-radius: 8px; text-decoration: none; color: var(--muted); font-size: 13px; font-weight: 550; transition: background .15s, color .15s; }
.cabinet-nav-link > svg { width: 17px; font-size: 15px; }
.cabinet-nav-link:hover { background: var(--control); color: var(--text); }
.cabinet-nav-link.is-active { color: var(--accent); background: var(--accent-soft); }
.cabinet-nav-link .nav-arrow { margin-left: auto; width: 8px; font-size: 10px; }
.cabinet-sidebar-bottom { padding: 16px; }
.cabinet-site-link { display: flex; gap: 12px; align-items: center; padding: 12px; color: var(--muted); text-decoration: none; font-size: 12px; }
.cabinet-sidebar-user { display: flex; align-items: center; gap: 10px; margin-top: 12px; padding: 16px 8px 0; border-top: 1px solid var(--panel-border); }
.cabinet-sidebar-user div { min-width: 0; }
.cabinet-sidebar-user strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cabinet-avatar { display: grid; place-items: center; flex-shrink: 0; width: 35px; height: 35px; background: var(--accent-soft); color: var(--accent); border: 1px solid var(--panel-border); border-radius: 50%; font-size: 13px; font-weight: 700; }
.cabinet-workarea { display: flex; flex: 1; min-width: 0; flex-direction: column; margin-left: 248px; }
.cabinet-topbar { position: sticky; top: 0; height: 68px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 32px; background: var(--surface); border-bottom: 1px solid var(--panel-border); z-index: 40; }
.cabinet-breadcrumb { display: flex; align-items: center; gap: 14px; min-width: 0; font-size: 12px; }
.breadcrumb-root, .breadcrumb-divider { color: var(--muted); }
.breadcrumb-divider { font-size: 8px; }
.breadcrumb-current { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 600; }
.cabinet-topbar-actions { display: flex; align-items: center; gap: 6px; }
.cabinet-icon-button { display: grid; place-items: center; flex-shrink: 0; width: 36px; height: 36px; border: 1px solid transparent; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; font-size: 14px; }
.cabinet-icon-button:hover { color: var(--text); background: var(--control); border-color: var(--panel-border); }
.cabinet-logout:hover { color: var(--danger); }
.cabinet-icon-button:disabled { opacity: .5; cursor: wait; }
.topbar-separator { height: 22px; width: 1px; background: var(--panel-border); margin: 0 7px; }
.cabinet-main { flex: 1; width: 100%; max-width: 1600px; margin: 0 auto; padding: 32px; min-width: 0; outline: none; }
.cabinet-footer { display: flex; justify-content: space-between; padding: 18px 32px; font-size: 11px; color: var(--muted); }
.cabinet-password-notice { display: flex; align-items: center; gap: 10px; padding: 12px 32px; background: var(--warning-soft); color: var(--warning); font-size: 13px; }
.cabinet-password-notice button { margin-left: auto; border: 0; color: inherit; background: transparent; font-weight: 700; cursor: pointer; min-height: 36px; }
.cabinet-menu-button, .sidebar-close { display: none; }
.cabinet-skip { position: fixed; top: -80px; left: 16px; z-index: 200; padding: 14px; background: var(--surface); color: var(--text); border: 2px solid var(--accent); border-radius: 8px; }
.cabinet-skip:focus { top: 12px; }
@media (max-width: 1023px) {
  .cabinet-sidebar { transform: translateX(-100%); visibility: hidden; transition: transform .2s, visibility .2s; box-shadow: var(--cabinet-shadow); width: 280px; max-width: calc(100vw - 48px); }
  .cabinet-sidebar.is-open { transform: translateX(0); visibility: visible; }
  .cabinet-overlay { position: fixed; inset: 0; z-index: 60; background: #0b122980; backdrop-filter: blur(3px); }
  .cabinet-workarea { margin-left: 0; }
  .cabinet-menu-button, .sidebar-close { display: grid; }
  .cabinet-topbar { padding: 0 24px; }
  .cabinet-main { padding: 24px; }
}
@media (max-width: 600px) {
  .cabinet-topbar { height: 64px; padding: 0 12px; gap: 4px; }
  .cabinet-breadcrumb { gap: 8px; }
  .breadcrumb-root, .breadcrumb-divider, .topbar-avatar, .topbar-separator { display: none; }
  .cabinet-topbar-actions { gap: 0; }
  .cabinet-icon-button { width: 40px; height: 44px; }
  .cabinet-main { padding: 22px 16px; }
  .cabinet-footer { padding: 16px; }
  .cabinet-password-notice { padding: 10px 16px; font-size: 12px; }
}
@media (prefers-reduced-motion: reduce) { .cabinet-sidebar, .cabinet-nav-link { transition: none; } }
</style>
