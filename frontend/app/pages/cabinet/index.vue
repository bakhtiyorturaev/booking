<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCalendarCheck, faBuilding, faUsers, faWallet, faArrowRotateRight, faArrowRight, faClock, faCircleCheck, faCalendar } from "@fortawesome/free-solid-svg-icons"
import { useAdminApi } from "~/api/admin"

definePageMeta({
  alias: ["/site/staff/panel", "/site/client/panel"], layout: "admin", middleware: ["admin"] })
useHead({ title: "Umumiy ko‘rinish" })

interface RecentBooking {
  id: string
  user_name: string
  user_phone: string
  club_name: string
  branch_name: string
  zone_name: string
  starts_at: string
  ends_at: string
  status: string
  total_price_tiyin: number
}
interface DashboardStats {
  clubs: { total: number; active: number; pending: number }
  branches: { total: number; active: number }
  bookings: { today: number; active_now: number; pending: number; completed: number; cancelled: number }
  users: { total: number; active: number; staff: number }
  revenue: { today_tiyin: number; total_tiyin: number }
  recent_bookings: RecentBooking[]
}
const cabinetPath = useCabinetPath()
const adminApi = useAdminApi()
const stats = ref<DashboardStats | null>(null)
const isLoading = ref(true)
const errorMessage = ref("")
const busyBooking = ref("")
const updatedAt = ref<Date | null>(null)
const todayLabel = ref("")
const statusLabels: Record<string, string> = { CONFIRMED: "Tasdiqlangan", CHECKED_IN: "Boshlangan", COMPLETED: "Tugallangan", CANCELLED: "Bekor qilingan", PENDING_CONFIRMATION: "Kutilmoqda", NO_SHOW: "Kelmadi" }
const formatPrice = (tiyin: number) => new Intl.NumberFormat("uz-UZ").format(Math.round((tiyin || 0) / 100))
const formatTime = (value: string) => new Date(value).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tashkent" })
const formatDay = (value: string) => new Date(value).toLocaleDateString("uz-UZ", { day: "2-digit", month: "2-digit", timeZone: "Asia/Tashkent" })
const updatedLabel = computed(() => updatedAt.value?.toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Tashkent" }))
const fetchStats = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try { stats.value = await adminApi.getStats(); updatedAt.value = new Date() }
  catch { errorMessage.value = "Ma’lumotlarni yuklab bo‘lmadi." }
  finally { isLoading.value = false }
}
const changeBooking = async (booking: RecentBooking) => {
  if (busyBooking.value) return
  busyBooking.value = booking.id
  try {
    if (booking.status === "CONFIRMED") await adminApi.checkInBooking(booking.id)
    else await adminApi.completeBooking(booking.id)
    useToast().success(booking.status === "CONFIRMED" ? "Bron boshlandi" : "Bron tugallandi")
    await fetchStats()
  } catch { useToast().error("Amalni bajarib bo‘lmadi. Qayta urinib ko‘ring.") }
  finally { busyBooking.value = "" }
}
onMounted(() => {
  const months = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
  const parts = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "numeric", year: "numeric", timeZone: "Asia/Tashkent" }).formatToParts(new Date())
  const part = (name: string) => parts.find(value => value.type === name)?.value || ""
  todayLabel.value = `${Number(part("day"))} ${months[Number(part("month")) - 1]} ${part("year")}`
  void fetchStats()
})
</script>

<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <div><h1 class="page-title">Umumiy ko‘rinish</h1><span class="dashboard-date"><FontAwesomeIcon :icon="faCalendar" />{{ todayLabel }}</span></div>
      <button type="button" class="secondary-button" :disabled="isLoading" @click="fetchStats"><FontAwesomeIcon :icon="faArrowRotateRight" :class="{ 'is-spinning': isLoading }" />Yangilash</button>
    </div>
    <div v-if="errorMessage" class="error-banner" role="alert"><p>{{ errorMessage }}</p><button type="button" class="secondary-button" @click="fetchStats">Qayta urinish</button></div>
    <div v-else-if="isLoading && !stats" class="dashboard-skeleton" role="status" aria-label="Ma’lumotlar yuklanmoqda"><span v-for="n in 4" :key="n" /><div /><p class="sr-only">Yuklanmoqda</p></div>
    <div v-else-if="stats" class="dashboard-content" :aria-busy="isLoading">
      <div class="metric-grid">
        <NuxtLink :to="cabinetPath('/bookings')" class="metric-card"><div class="metric-top"><span>Bugungi bronlar</span><span class="metric-icon violet"><FontAwesomeIcon :icon="faCalendarCheck" /></span></div><strong class="metric-value">{{ stats.bookings.today }}</strong><div class="metric-bottom"><span class="metric-pill"><span class="metric-dot" />{{ stats.bookings.active_now }} davom etmoqda</span><FontAwesomeIcon :icon="faArrowRight" /></div></NuxtLink>
        <NuxtLink :to="cabinetPath('/payments')" class="metric-card"><div class="metric-top"><span>Bugungi tushum</span><span class="metric-icon green"><FontAwesomeIcon :icon="faWallet" /></span></div><strong class="metric-value">{{ formatPrice(stats.revenue.today_tiyin) }}<small>so‘m</small></strong><div class="metric-bottom"><span>Jami {{ formatPrice(stats.revenue.total_tiyin) }} so‘m</span><FontAwesomeIcon :icon="faArrowRight" /></div></NuxtLink>
        <NuxtLink :to="cabinetPath('/clubs')" class="metric-card"><div class="metric-top"><span>Muassasalar</span><span class="metric-icon amber"><FontAwesomeIcon :icon="faBuilding" /></span></div><strong class="metric-value">{{ stats.clubs.total }}</strong><div class="metric-bottom"><span>{{ stats.clubs.active }} faol <span class="metric-divider">/</span> {{ stats.branches.total }} filial</span><FontAwesomeIcon :icon="faArrowRight" /></div></NuxtLink>
        <NuxtLink :to="cabinetPath('/users')" class="metric-card"><div class="metric-top"><span>Foydalanuvchilar</span><span class="metric-icon blue"><FontAwesomeIcon :icon="faUsers" /></span></div><strong class="metric-value">{{ stats.users.total }}</strong><div class="metric-bottom"><span>{{ stats.users.active }} faol <span class="metric-divider">/</span> {{ stats.users.staff }} xodim</span><FontAwesomeIcon :icon="faArrowRight" /></div></NuxtLink>
      </div>
      <div class="dashboard-columns">
        <section class="dashboard-section bookings-section" aria-labelledby="recent-bookings-title">
          <div class="section-top"><div class="section-title-row"><h2 id="recent-bookings-title">Oxirgi bronlar</h2><span class="section-count">{{ stats.recent_bookings.length }}</span></div><NuxtLink :to="cabinetPath('/bookings')" class="section-link">Barchasi<FontAwesomeIcon :icon="faArrowRight" /></NuxtLink></div>
          <div v-if="!stats.recent_bookings.length" class="dashboard-empty"><span class="empty-icon"><FontAwesomeIcon :icon="faCalendarCheck" /></span><strong>Hali bronlar yo‘q</strong><NuxtLink :to="cabinetPath('/bookings')">Bronlar sahifasi<FontAwesomeIcon :icon="faArrowRight" /></NuxtLink></div>
          <div v-else class="table-container"><table class="admin-table"><caption class="sr-only">Oxirgi bronlar</caption><thead><tr><th scope="col">Mijoz</th><th scope="col">Muassasa</th><th scope="col">Vaqt</th><th scope="col">Summa</th><th scope="col">Holat</th><th scope="col">Amal</th></tr></thead><tbody><tr v-for="b in stats.recent_bookings" :key="b.id">
            <td data-label="Mijoz"><div class="booking-person"><span class="person-avatar">{{ b.user_name.slice(0, 1).toUpperCase() }}</span><div><strong>{{ b.user_name }}</strong><span>{{ b.user_phone || '—' }}</span></div></div></td>
            <td data-label="Muassasa"><div class="table-stack"><strong>{{ b.club_name }}</strong><span>{{ b.branch_name }} · {{ b.zone_name }}</span></div></td>
            <td data-label="Vaqt"><div class="table-stack"><strong>{{ formatTime(b.starts_at) }}–{{ formatTime(b.ends_at) }}</strong><span>{{ formatDay(b.starts_at) }}</span></div></td>
            <td data-label="Summa"><span class="price-text">{{ formatPrice(b.total_price_tiyin) }} so‘m</span></td>
            <td data-label="Holat"><span class="status-badge" :class="b.status.toLowerCase()">{{ statusLabels[b.status] || b.status }}</span></td>
            <td data-label="Amal"><button v-if="['CONFIRMED', 'CHECKED_IN'].includes(b.status)" type="button" class="btn-action checkin" :disabled="Boolean(busyBooking)" @click="changeBooking(b)">{{ busyBooking === b.id ? 'Kutilmoqda…' : b.status === 'CONFIRMED' ? 'Boshlash' : 'Tugatish' }}</button><span v-else class="table-muted">—</span></td>
          </tr></tbody></table></div>
          <div class="section-bottom"><FontAwesomeIcon :icon="faClock" /><span>Yangilandi {{ updatedLabel }}</span></div>
        </section>
        <section class="dashboard-section attention-section" aria-labelledby="attention-title"><div class="section-top"><h2 id="attention-title">E’tibor talab qiladi</h2></div>
          <NuxtLink :to="cabinetPath('/bookings')" class="attention-item"><span class="attention-icon amber"><FontAwesomeIcon :icon="faClock" /></span><span class="attention-text"><strong>Kutilayotgan bronlar</strong><span>Tasdiqlash</span></span><strong class="attention-count">{{ stats.bookings.pending }}</strong><FontAwesomeIcon :icon="faArrowRight" /></NuxtLink>
          <NuxtLink :to="cabinetPath('/clubs')" class="attention-item"><span class="attention-icon violet"><FontAwesomeIcon :icon="faBuilding" /></span><span class="attention-text"><strong>Yangi muassasalar</strong><span>Tekshirish</span></span><strong class="attention-count">{{ stats.clubs.pending }}</strong><FontAwesomeIcon :icon="faArrowRight" /></NuxtLink>
          <div class="activity-summary"><span class="activity-icon"><FontAwesomeIcon :icon="faCircleCheck" /></span><div><strong>{{ stats.bookings.completed }}</strong><span>Tugallangan bronlar</span></div><div class="cancelled-summary"><strong>{{ stats.bookings.cancelled }}</strong><span>Bekor qilingan</span></div></div>
        </section>
      </div>

    </div>
  </div>
</template>

<style scoped>
.admin-dashboard, .dashboard-content { display: flex; flex-direction: column; gap: 24px; min-width: 0; }
.dashboard-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.dashboard-date { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); margin-top: 10px; }
.dashboard-date svg { font-size: 11px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.metric-card { text-decoration: none; color: var(--text); background: var(--surface); border: 1px solid var(--panel-border); border-radius: 12px; padding: 20px; min-width: 0; transition: border-color .2s; }
.metric-card:hover { border-color: var(--accent); }
.metric-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 12px; font-weight: 550; color: var(--muted); }
.metric-icon, .attention-icon { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 9px; font-size: 14px; flex-shrink: 0; }
.violet { background: var(--accent-soft); color: var(--accent); }
.green { background: var(--success-soft); color: var(--success); }
.amber { background: var(--warning-soft); color: var(--warning); }
.blue { background: color-mix(in srgb, #548ee9 12%, var(--surface)); color: #548ee9; }
.metric-value { display: flex; flex-wrap: wrap; align-items: baseline; gap: 7px; margin-top: 16px; font-size: clamp(24px, 2.5vw, 34px); line-height: 1.2; letter-spacing: -1px; font-weight: 650; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.metric-value small { font-size: 12px; font-weight: 500; color: var(--muted); letter-spacing: 0; }
.metric-bottom { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 18px; font-size: 10px; color: var(--muted); }
.metric-bottom > svg { font-size: 10px; opacity: .6; }
.metric-divider { padding: 0 4px; color: var(--border); }
.metric-pill { display: inline-flex; align-items: center; gap: 5px; color: var(--success); }
.metric-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--success); }
.dashboard-columns { display: grid; grid-template-columns: minmax(0, 1fr) 300px; align-items: start; gap: 24px; }
.section-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 20px; border-bottom: 1px solid var(--panel-border); }
.section-top h2 { margin: 0; font-size: 14px; font-weight: 650; letter-spacing: -.2px; }
.section-title-row { display: flex; align-items: center; gap: 8px; }
.section-count { padding: 3px 7px; border-radius: 5px; background: var(--control); color: var(--muted); font-size: 10px; }
.section-link { display: flex; align-items: center; gap: 8px; text-decoration: none; color: var(--accent); font-size: 11px; white-space: nowrap; }
.section-link:hover { text-decoration: underline; }
.booking-person { display: flex; align-items: center; gap: 9px; }
.person-avatar { display: grid; place-items: center; width: 32px; height: 32px; flex-shrink: 0; font-size: 11px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); font-weight: 650; }
.booking-person strong, .table-stack strong { display: block; font-size: 12px; font-weight: 600; }
.booking-person div > span, .table-stack > span { display: block; margin-top: 3px; font-size: 10px; color: var(--muted); }
.table-stack { min-width: 105px; }
.table-muted { color: var(--muted); }
.section-bottom { display: flex; align-items: center; gap: 6px; padding: 12px 20px; background: var(--control); border-top: 1px solid var(--panel-border); color: var(--muted); font-size: 10px; }
.attention-item { display: flex; align-items: center; gap: 10px; padding: 20px 16px; border-bottom: 1px solid var(--panel-border); text-decoration: none; color: var(--text); }
.attention-item:hover { background: var(--control); }
.attention-item > svg { color: var(--muted); font-size: 9px; }
.attention-text { flex: 1; min-width: 0; }
.attention-text strong { display: block; font-size: 11px; font-weight: 600; }
.attention-text > span { display: block; margin-top: 5px; color: var(--muted); font-size: 10px; }
.attention-count { font-size: 18px; font-weight: 650; }
.activity-summary { display: flex; align-items: center; padding: 20px 16px; gap: 8px; }
.activity-icon { color: var(--success); font-size: 13px; }
.activity-summary strong { display: block; font-size: 16px; font-weight: 650; }
.activity-summary div > span { display: block; margin-top: 4px; color: var(--muted); font-size: 9px; }
.cancelled-summary { margin-left: auto; text-align: right; }
.dashboard-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; min-height: 260px; padding: 32px; font-size: 13px; }
.empty-icon { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 14px; background: var(--control); color: var(--muted); font-size: 19px; }
.dashboard-empty strong { font-weight: 550; color: var(--muted); }
.dashboard-empty a { display: flex; gap: 8px; align-items: center; font-size: 11px; text-decoration: none; color: var(--accent); }
.compact-empty { min-height: 160px; }
.dashboard-skeleton { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.dashboard-skeleton > span { height: 170px; border: 1px solid var(--panel-border); border-radius: 12px; background: var(--surface); }
.dashboard-skeleton > div { height: 320px; background: var(--surface); border: 1px solid var(--panel-border); border-radius: 12px; grid-column: 1 / -1; }
.is-spinning { animation: rotate 1s linear infinite; }
@keyframes rotate { to { transform: rotate(360deg); } }
@media (max-width: 1280px) { .dashboard-columns { grid-template-columns: 1fr; } .attention-section { display: grid; grid-template-columns: 1fr 1fr; } .attention-section .section-top { grid-column: 1 / -1; } .activity-summary { grid-column: 1 / -1; } }
@media (max-width: 1150px) { .metric-grid, .dashboard-skeleton { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 700px) { .admin-dashboard, .dashboard-content { gap: 20px; } .metric-grid { gap: 12px; } .metric-card { padding: 14px; } .metric-top { font-size: 11px; align-items: start; } .metric-icon { width: 28px; height: 28px; font-size: 12px; } .metric-value { font-size: 25px; margin-top: 12px; } .metric-bottom { font-size: 9px; margin-top: 14px; } .metric-bottom > svg { display: none; } .dashboard-header { align-items: start; } .dashboard-header .secondary-button { padding: 10px 12px; min-height: 44px; } .section-top { padding: 18px 16px; } .dashboard-columns { gap: 20px; } .attention-section { display: block; } }
@media (max-width: 360px) { .metric-grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .is-spinning { animation: none; } }
</style>
