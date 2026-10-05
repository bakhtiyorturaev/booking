<script setup lang="ts">
import FreeModeToggle from "~/components/cabinet/FreeModeToggle.vue"
import VenueBillingBadge from "~/components/cabinet/VenueBillingBadge.vue"
import { useAdminApi } from "~/api/admin"
import type { BillingVenue, ManualVenuePayment, ManualPaymentInput, BillingSummary } from "~/types/venueBilling"

definePageMeta({
  alias: ["/site/staff/panel/payments", "/site/client/panel/payments"], layout: "admin", middleware: ["admin"] })
useHead({ title: "To‘lovlar" })
const cabinetPath = useCabinetPath()
const api = useAdminApi()
const { user } = useAuth()
const isStaff = computed(() => user.value?.is_staff || user.value?.is_superuser || ["ADMIN", "MODERATOR"].includes(user.value?.role || ""))
const tab = ref<"venues" | "barbers" | "history">("venues")
const paymentKind = ref<"venue" | "barber">("venue")
const venues = ref<BillingVenue[]>([])
const payments = ref<ManualVenuePayment[]>([])
const summary = ref<BillingSummary | null>(null)
const query = ref("")
const page = ref(1)
const count = ref(0)
const hasNext = ref(false)
const loading = ref(true)
const error = ref("")
const money = (tiyin: number | null) => tiyin === null ? "—" : `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(tiyin / 100)} so‘m`
const date = (value: string | null) => value ? new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "—"
let loadVersion = 0
const load = async () => {
  const version = ++loadVersion
  loading.value = true; error.value = ""
  try {
    const params = { query: query.value.trim(), page: page.value }
    if (tab.value !== "history") {
      const response = await (tab.value === "barbers" ? api.getBarberBilling(params) : api.getBranchBilling(params))
      if (version !== loadVersion) return
      venues.value = response.results; count.value = response.count; hasNext.value = Boolean(response.next)
    } else {
      const response = await api.getVenuePayments(params)
      if (version !== loadVersion) return
      payments.value = response.results; count.value = response.count; hasNext.value = Boolean(response.next)
    }
    const result = await api.getVenuePaymentSummary()
    if (version === loadVersion) summary.value = result
  } catch (e) { if (version === loadVersion) error.value = cabinetErrorMessage(e) }
  finally { if (version === loadVersion) loading.value = false }
}
watch(tab, () => { page.value = 1; void load() })
const search = () => { page.value = 1; void load() }
const changePage = (value: number) => { page.value = value; void load() }
onMounted(load)

const showPayment = ref(false)
const saving = ref(false)
const modalError = ref("")
const choices = ref<BillingVenue[]>([])
const venueQuery = ref("")
const searchingVenues = ref(false)
const form = ref<ManualPaymentInput>({ club: "", amount: "", method: "CASH", note: "", idempotency_key: "" })
const selectedVenue = computed(() => choices.value.find(venue => venue.id === (form.value.club || form.value.barber)))
const toTiyin = (value: string | number) => {
  const text = String(value)
  if (!/^\d{1,12}(?:\.\d{1,2})?$/.test(text)) return 0
  const [whole = "0", fraction = ""] = text.split(".")
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"))
}
const days = computed(() => selectedVenue.value?.monthly_price_tiyin ? toTiyin(form.value.amount) * 30 / selectedVenue.value.monthly_price_tiyin : 0)
const projectedExpiry = computed(() => {
  if (!days.value) return null
  const base = Math.max(Date.now(), selectedVenue.value?.paid_until ? Date.parse(selectedVenue.value.paid_until) : 0)
  const result = new Date(base + days.value * 86400000)
  return Number.isFinite(result.getTime()) ? result.toISOString() : null
})
const closePayment = () => { if (!saving.value) showPayment.value = false }
useDialogFocus(showPayment, "#manual-payment-dialog", closePayment)
const searchVenues = async () => {
  searchingVenues.value = true
  try {
    const response = await (paymentKind.value === "barber" ? api.getBarberBilling({ query: venueQuery.value.trim(), page_size: 100 }) : api.getVenueBilling({ query: venueQuery.value.trim(), page_size: 100 }))
    const selected = selectedVenue.value
    choices.value = response.results.filter(venue => venue.billing_enabled)
    if (selected && !choices.value.some(venue => venue.id === selected.id)) choices.value.unshift(selected)
  } catch (e) { modalError.value = cabinetErrorMessage(e) }
  finally { searchingVenues.value = false }
}
const openPayment = async (venue?: BillingVenue) => {
  if (venue?.club_id) venue = { ...venue, id: venue.club_id, name: venue.club_name || venue.name }
  paymentKind.value = tab.value === "barbers" ? "barber" : "venue"
  modalError.value = ""; venueQuery.value = ""
  choices.value = venue ? [venue] : []
  form.value = { ...(paymentKind.value === "barber" ? { barber: venue?.id || "" } : { club: venue?.id || "" }), amount: "", method: "CASH", note: "", idempotency_key: crypto.randomUUID() }
  showPayment.value = true
  if (!venue) await searchVenues()
}
watch(() => [form.value.club, form.value.barber, form.value.amount, form.value.method, form.value.note], () => {
  if (showPayment.value && !saving.value) form.value.idempotency_key = crypto.randomUUID()
}, { flush: "sync" })
const recordPayment = async () => {
  if (saving.value) return
  if (!selectedVenue.value?.monthly_price_tiyin || !toTiyin(form.value.amount)) { modalError.value = "Muassasani tanlang va musbat to‘lov summasini kiriting."; return }
  saving.value = true; modalError.value = ""
  try {
    const payment = await api.recordVenuePayment({ ...form.value, amount: String(form.value.amount) })
    showPayment.value = false
    useToast().success(`To‘lov saqlandi. Muddat: ${date(payment.period_ends_at)}`)
    await load()
  } catch (e) { modalError.value = cabinetErrorMessage(e) }
  finally { saving.value = false }
}
</script>

<template>
  <div class="admin-page">
    <div class="page-header"><h1 class="page-title">To‘lovlar</h1><button v-if="isStaff" class="primary-button" type="button" @click="openPayment()"><CabinetIcon name="plus" /> To‘lov kiritish</button></div>
    <div v-if="summary" class="billing-summary">
      <div class="summary-card"><span>Jami tushum</span><strong>{{ money(summary.total_tiyin) }}</strong><small>{{ summary.count }} ta to‘lov</small></div>
      <div class="summary-card"><span>Bugun</span><strong>{{ money(summary.today_tiyin) }}</strong></div>
      <div class="summary-card"><span>Naqd</span><strong>{{ money(summary.cash_tiyin) }}</strong></div>
      <div class="summary-card"><span>Karta</span><strong>{{ money(summary.card_tiyin) }}</strong></div>
    </div>
    <div class="billing-toolbar"><div class="status-tabs-nav" aria-label="To‘lov bo‘limlari"><button class="tab-btn" :class="{ 'is-active': tab === 'venues' }" type="button" :aria-pressed="tab === 'venues'" @click="tab = 'venues'">Filiallar</button><button class="tab-btn" :class="{ 'is-active': tab === 'barbers' }" type="button" :aria-pressed="tab === 'barbers'" @click="tab = 'barbers'">Sartaroshlar</button><button class="tab-btn" :class="{ 'is-active': tab === 'history' }" type="button" :aria-pressed="tab === 'history'" @click="tab = 'history'">To‘lovlar tarixi</button></div></div>
    <form class="filter-bar" @submit.prevent="search"><div class="search-wrap"><input v-model="query" type="search" aria-label="Muassasa yoki egasi" placeholder="Muassasa yoki egasi" class="billing-search"></div><button class="secondary-button" type="submit" :disabled="loading">Qidirish</button></form>
    <div v-if="error" class="error-banner" role="alert">{{ error }}</div>
    <div v-if="loading" class="loading-container">Yuklanmoqda…</div>
    <div v-else class="table-card">
      <div v-if="!count" class="empty-state">{{ tab === 'venues' ? 'Filiallar topilmadi.' : tab === 'barbers' ? 'Sartaroshlar topilmadi.' : 'To‘lovlar hali kiritilmagan.' }}</div>
      <div v-else class="table-container">
        <table v-if="tab !== 'history'" class="admin-table">
          <thead><tr><th scope="col">Muassasa</th><th scope="col">Egasi</th><th scope="col">30 kunlik narx</th><th scope="col">To‘langan muddat</th><th scope="col">Holat</th><th v-if="isStaff" scope="col">Bepul rejim</th><th scope="col">Amallar</th></tr></thead>
          <tbody><tr v-for="venue in venues" :key="venue.id">
            <td data-label="Muassasa"><strong>{{ venue.name }}</strong></td><td data-label="Egasi">{{ venue.owner_name }}</td><td data-label="30 kunlik narx" class="price-val">{{ money(venue.monthly_price_tiyin) }}</td><td data-label="To‘langan muddat">{{ date(venue.paid_until) }}</td>
            <td data-label="Holat"><VenueBillingBadge :billing="venue" /></td>
            <td v-if="isStaff" data-label="Bepul rejim"><FreeModeToggle :kind="tab === 'barbers' ? 'barber' : 'branch'" :id="venue.id" :name="venue.name" :is-free="Boolean(venue.is_free)" @changed="load" /></td>
            <td data-label="Amallar"><div class="action-buttons-inline"><template v-if="isStaff"><button v-if="venue.billing_enabled && venue.monthly_price_tiyin" class="btn-act checkin" type="button" @click="openPayment(venue)">To‘lov kiritish</button></template><NuxtLink :to="{ path: cabinetPath(tab === 'barbers' ? '/barbers' : '/branches'), query: { query: venue.name } }" class="btn-act">Muassasa</NuxtLink></div></td>
          </tr></tbody>
        </table>
        <table v-else class="admin-table">
          <thead><tr><th scope="col">Muassasa / mijoz</th><th scope="col">Summa</th><th scope="col">Usul</th><th scope="col">Qo‘shilgan muddat</th><th scope="col">Amal qilish davri</th><th scope="col">Xodim / sana</th></tr></thead>
          <tbody><tr v-for="payment in payments" :key="payment.id">
            <td data-label="Muassasa / mijoz"><strong>{{ payment.barber_name || payment.club_name }}</strong><small class="billing-sub">{{ payment.client_name }}</small><small v-if="payment.note" class="billing-sub">{{ payment.note }}</small></td><td data-label="Summa" class="price-val">{{ money(payment.amount_tiyin) }}<small class="billing-sub">Tarif: {{ money(payment.monthly_price_tiyin) }}</small></td><td data-label="Usul">{{ payment.method === 'CASH' ? 'Naqd' : 'Karta' }}</td><td data-label="Qo‘shilgan muddat">{{ Number(payment.duration_days).toLocaleString('ru-RU', { maximumFractionDigits: 6 }) }} kun</td><td data-label="Amal qilish davri">{{ date(payment.period_starts_at) }}<small class="billing-sub">{{ date(payment.period_ends_at) }} gacha</small></td><td data-label="Xodim / sana">{{ payment.received_by_name }}<small class="billing-sub">{{ date(payment.created_at) }}</small></td>
          </tr></tbody>
        </table>
      </div>
      <div v-if="count > 20" class="cabinet-pagination"><span>{{ page }}-sahifa · {{ count }} ta</span><div><button class="secondary-button" type="button" :disabled="page === 1" @click="changePage(page - 1)">Oldingi</button><button class="secondary-button" type="button" :disabled="!hasNext" @click="changePage(page + 1)">Keyingi</button></div></div>
    </div>
    <Teleport to="body">
      <div v-if="showPayment" id="manual-payment-dialog" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" aria-labelledby="manual-payment-title" tabindex="-1" @click.self="closePayment">
        <div class="modal-card billing-dialog"><div class="modal-header"><h2 id="manual-payment-title">To‘lov kiritish</h2><button class="modal-close-btn" type="button" aria-label="Yopish" :disabled="saving" @click="closePayment"><CabinetIcon name="close" /></button></div>
          <form class="modal-form" @submit.prevent="recordPayment">
            <p v-if="modalError" class="form-error" role="alert">{{ modalError }}</p>
            <fieldset :disabled="saving" class="billing-fields">
              <div class="form-group"><label for="payment-kind">To‘lov kim uchun</label><select id="payment-kind" v-model="paymentKind" @change="form.club = undefined; form.barber = undefined; choices = []; searchVenues()"><option value="venue">Muassasa</option><option value="barber">Sartarosh</option></select></div>
              <div class="form-group"><label for="payment-venue-query">Muassasa izlash</label><div class="billing-picker"><input id="payment-venue-query" v-model="venueQuery" type="search" placeholder="Muassasa yoki egasi" @keydown.enter.prevent="searchVenues"><button class="secondary-button" type="button" :disabled="searchingVenues" @click="searchVenues">Qidirish</button></div></div>
              <div class="form-group"><label for="payment-venue">{{ paymentKind === 'barber' ? 'Sartarosh' : 'Muassasa' }}</label><select id="payment-venue"  :value="form.club || form.barber || ''" @change="event => { if (paymentKind === 'barber') form.barber = (event.target as HTMLSelectElement).value; else form.club = (event.target as HTMLSelectElement).value }" required><option value="" disabled>Muassasani tanlang</option><option v-for="venue in choices" :key="venue.id" :value="venue.id">{{ venue.name }} — {{ venue.owner_name }}</option></select></div>
              <p v-if="selectedVenue && !selectedVenue.monthly_price_tiyin" class="form-error">Bu muassasa uchun avval tarif belgilang.</p>
              <div class="form-row"><div class="form-group"><label for="payment-amount">To‘lov summasi, so‘m</label><input id="payment-amount" v-model="form.amount" type="number" inputmode="decimal" min="0.01" max="999999999999.99" step="0.01" required placeholder="50 000"></div><div class="form-group"><label for="payment-method">To‘lov usuli</label><select id="payment-method" v-model="form.method"><option value="CASH">Naqd</option><option value="CARD">Karta</option></select></div></div>
              <div v-if="selectedVenue?.monthly_price_tiyin" class="billing-preview" aria-live="polite"><div><span>30 kunlik narx</span><strong>{{ money(selectedVenue.monthly_price_tiyin) }}</strong></div><div><span>Qo‘shiladigan muddat</span><strong>{{ days.toLocaleString('ru-RU', { maximumFractionDigits: 6 }) }} kun</strong></div><div><span>Taxminiy tugash vaqti</span><strong>{{ date(projectedExpiry) }}</strong></div></div>
              <div class="form-group"><label for="payment-note">Izoh</label><textarea id="payment-note" v-model="form.note" maxlength="500" rows="2" /></div>
            </fieldset>
            <div class="modal-actions"><button type="button" class="secondary-button" :disabled="saving" @click="closePayment">Bekor qilish</button><button type="submit" class="primary-button" :disabled="saving || !selectedVenue?.monthly_price_tiyin || !days">{{ saving ? 'Saqlanmoqda…' : 'To‘lovni saqlash' }}</button></div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.billing-mode-badge { padding: 12px 16px; border: 1px solid var(--panel-border); border-radius: 10px; color: var(--success); background: var(--success-soft); }
.billing-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.summary-card { display: flex; flex-direction: column; gap: 12px; padding: 20px; border: 1px solid var(--panel-border); }
.summary-card > span, .summary-card small { color: var(--muted); font-size: 12px; }
.summary-card strong { font-size: clamp(17px, 1.6vw, 24px); letter-spacing: -.5px; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.billing-search { width: 100%; }
.billing-sub { display: block; margin-top: 4px; font-size: 11px; color: var(--muted); font-weight: 400; }
.billing-dialog { width: min(560px, 100%); }
.billing-fields { padding: 0; margin: 0; border: 0; min-width: 0; display: grid; gap: 18px; }
.billing-picker { display: flex; align-items: center; gap: 8px; }
.billing-picker input { flex: 1; min-width: 0; }
.billing-preview { padding: 16px; border: 1px solid var(--panel-border); border-radius: 10px; background: var(--accent-soft); display: grid; gap: 12px; }
.billing-preview > div { display: flex; justify-content: space-between; gap: 12px; font-size: 12px; }
.billing-preview span { color: var(--muted); }
.billing-preview strong { text-align: right; font-variant-numeric: tabular-nums; }
.billing-venue-name { margin: 0; font-weight: 600; }
@media (max-width: 900px) { .billing-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; } .summary-card { padding: 16px; } }
@media (max-width: 450px) { .billing-preview > div { flex-direction: column; gap: 4px; } .billing-preview strong { text-align: left; } }
</style>
