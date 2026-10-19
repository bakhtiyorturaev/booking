<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faPlus, faXmark } from "@fortawesome/free-solid-svg-icons"
import { useAdminApi } from "~/api/admin"
import RemoteSelect from "~/components/ui/RemoteSelect.vue"
import type { SearchSelectOption, SearchSelectPage } from "~/types/searchSelect"

interface Account { id: string; username: string; phone?: string; profile?: { full_name?: string } }
interface Salon { id: string; name: string; address?: string }
interface Branch { id: string; name: string; address?: string; club: string | { id: string }; latitude?: string | number | null; longitude?: string | number | null }
const props = defineProps<{ clubId?: string; branchId?: string }>()
const emit = defineEmits<{ saved: [] }>()
const { isStaff } = useCabinetAccess()
const api = useAdminApi()
const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref("")
const session = ref(0)
const linked = ref(false)
const selectedUser = ref<SearchSelectOption | null>(null)
const selectedSalon = ref<SearchSelectOption | null>(null)
const selectedBranch = ref<SearchSelectOption | null>(null)
const accounts = new Map<string, Account>()
const branches = new Map<string, Branch>()
const cities = ref<{ id: string; name: string }[]>([])
const emptyForm = () => ({ user: "", resource: "", full_name: "", phone: "", billing_city: "", billing_district: "", latitude: null as number | null, longitude: null as number | null, work_start_time: "09:00", work_end_time: "20:00" })
const form = ref(emptyForm())
const { districts, isDistrictLoading, districtError } = useCityDistricts(() => form.value.billing_city)
const title = "Sartarosh qo‘shish"
const dialogId = "operator-barber-dialog"
let branchVersion = 0
const close = () => { if (!saving.value) { open.value = false; session.value++; branchVersion++ } }
useDialogFocus(open, `#${dialogId}`, close)
const searchUsers = async (query: string, page: number): Promise<SearchSelectPage> => {
  const response = await api.getUsers({ query, page, page_size: 15, status: "ACTIVE", available_for_barber: "true" })
  const records: Account[] = response.results || []
  records.forEach(account => accounts.set(account.id, account))
  return { options: records.map(account => ({ value: account.id, label: account.profile?.full_name || account.username, description: [account.phone, `@${account.username}`].filter(Boolean).join(" · ") })), hasNext: Boolean(response.next) }
}
const chooseUser = (option: SearchSelectOption | null) => {
  selectedUser.value = option
  form.value.user = option?.value || ""
  if (!option) return
  const account = accounts.get(option.value)
  form.value.full_name = account?.profile?.full_name || ""
  form.value.phone = account?.phone || ""
}
const searchSalons = async (query: string, page: number): Promise<SearchSelectPage> => {
  const response = await api.getClubs({ query, page, page_size: 15, category: "BARBERSHOP", status: "ACTIVE" })
  return { options: (response.results || []).map((salon: Salon) => ({ value: salon.id, label: salon.name, description: salon.address })), hasNext: Boolean(response.next) }
}
const searchBranches = async (query: string, page: number): Promise<SearchSelectPage> => {
  if (!selectedSalon.value) return { options: [], hasNext: false }
  const response = await api.getBranches({ query, page, page_size: 15, club_id: selectedSalon.value.value, status: "ACTIVE" })
  const records: Branch[] = response.results || []
  records.forEach(branch => branches.set(branch.id, branch))
  return { options: records.map(branch => ({ value: branch.id, label: branch.name, description: branch.address })), hasNext: Boolean(response.next) }
}
const chooseBranch = (option: SearchSelectOption | null) => {
  selectedBranch.value = option
  form.value.resource = option?.value || ""
  const branch = option ? branches.get(option.value) : undefined
  form.value.latitude = branch?.latitude != null && branch.latitude !== "" ? Number(branch.latitude) : null
  form.value.longitude = branch?.longitude != null && branch.longitude !== "" ? Number(branch.longitude) : null
}
const chooseSalon = async (option: SearchSelectOption | null) => {
  selectedSalon.value = option
  chooseBranch(null)
  const version = ++branchVersion
  if (!option) return
  try {
    const response = await api.getBranches({ club_id: option.value, status: "ACTIVE", page: 1, page_size: 1 })
    if (version !== branchVersion || !open.value) return
    if (response.count === 1 && response.results?.[0]) {
      const branch: Branch = response.results[0]
      branches.set(branch.id, branch)
      chooseBranch({ value: branch.id, label: branch.name, description: branch.address })
    }
  } catch (cause) { if (version === branchVersion) error.value = cabinetErrorMessage(cause) }
}
const setLinked = (value: boolean) => {
  if (props.clubId || props.branchId) return
  linked.value = value
  branchVersion++
  selectedSalon.value = null
  chooseBranch(null)
}
const begin = async () => {
  const current = ++session.value
  open.value = true; loading.value = true; error.value = ""
  form.value = emptyForm()
  selectedUser.value = null; selectedSalon.value = null; selectedBranch.value = null
  linked.value = Boolean(props.clubId || props.branchId)
  accounts.clear(); branches.clear()
  try {
    const [cityList, salon, branch] = await Promise.all([
      api.getCities(),
      props.clubId ? api.getClub(props.clubId) : Promise.resolve(null),
      props.branchId ? api.getBranch(props.branchId) : Promise.resolve(null),
    ])
    if (current !== session.value || !open.value) return
    cities.value = cityList.results || cityList.data || cityList || []
    if (salon) selectedSalon.value = { value: salon.id, label: salon.name }
    if (branch) {
      if (!selectedSalon.value) {
        const clubId = typeof branch.club === "string" ? branch.club : branch.club.id
        const club = await api.getClub(clubId)
        if (current !== session.value || !open.value) return
        selectedSalon.value = { value: club.id, label: club.name }
      }
      branches.set(branch.id, branch)
      chooseBranch({ value: branch.id, label: branch.name, description: branch.address })
    } else if (selectedSalon.value) await chooseSalon(selectedSalon.value)
  } catch (cause) { if (current === session.value) error.value = cabinetErrorMessage(cause) }
  finally { if (current === session.value) loading.value = false }
}
const coordinate = (value: unknown, limit: number) => value != null && value !== "" && Number.isFinite(Number(value)) && Math.abs(Number(value)) <= limit ? Number(value) : null
const save = async () => {
  if (saving.value) return
  error.value = ""
  if (!selectedUser.value) { error.value = "Akkauntni qidirib tanlang."; return }
  if (linked.value && (!selectedSalon.value || !selectedBranch.value)) { error.value = "Sartaroshxona va filialni tanlang."; return }
  const latitude = coordinate(form.value.latitude, 90)
  const longitude = coordinate(form.value.longitude, 180)
  if (latitude == null || longitude == null) { error.value = "Latitude va longitude qiymatlarini to‘g‘ri kiriting."; return }
  saving.value = true
  try {
    await api.createBarber({
      user: selectedUser.value.value, club: linked.value ? selectedSalon.value?.value : null,
      branch: linked.value ? selectedBranch.value?.value : null,
      billing_city: linked.value ? null : form.value.billing_city || null,
      billing_district: linked.value ? null : form.value.billing_district || null,
      latitude: latitude.toFixed(6), longitude: longitude.toFixed(6),
      full_name: form.value.full_name.trim(), phone: form.value.phone,
      affiliation_status: linked.value ? "APPROVED" : "NONE", status: "AVAILABLE",
      work_start_time: form.value.work_start_time, work_end_time: form.value.work_end_time,
      working_days: [1, 2, 3, 4, 5, 6, 7],
    })
    open.value = false; emit("saved"); useToast().success("Saqlandi.")
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally { saving.value = false }
}
</script>

<template>
  <button v-if="isStaff" type="button" class="primary-button" @click="begin"><FontAwesomeIcon :icon="faPlus" /> {{ title }}</button>
  <Teleport to="body">
    <div v-if="open" :id="dialogId" class="modal-backdrop cabinet-modal barber-dialog" role="dialog" aria-modal="true" :aria-labelledby="`${dialogId}-title`" tabindex="-1" @click.self="close">
      <div class="modal-card barber-dialog-card">
        <header class="barber-dialog-header"><h2 :id="`${dialogId}-title`">{{ title }}</h2><button type="button" class="close-button" aria-label="Yopish" :disabled="saving" @click="close"><FontAwesomeIcon :icon="faXmark" /></button></header>
        <form class="barber-form" :aria-busy="saving || loading" @submit.prevent="save">
          <div class="barber-dialog-body">
            <p v-if="error" class="form-error" role="alert">{{ error }}</p>
            <p v-if="loading" class="loading-state" role="status">Yuklanmoqda…</p>
            <template v-else>
              <div class="form-group"><label>Akkaunt <span>*</span></label><RemoteSelect :key="`user-${session}`" :model-value="selectedUser" :fetch-options="searchUsers" label="Akkaunt" placeholder="Ism, telefon yoki login bo‘yicha…" :disabled="saving" @update:model-value="chooseUser" /></div>
              <div class="field-grid"><div class="form-group"><label for="barber-full-name">Ism-familiya <span>*</span></label><input id="barber-full-name" v-model="form.full_name" required maxlength="180" :disabled="saving" autocomplete="name"></div><div class="form-group"><label for="barber-phone">Telefon</label><input id="barber-phone" v-model="form.phone" type="tel" maxlength="20" :disabled="saving" autocomplete="tel" placeholder="+998 90 123 45 67"></div></div>
              <div v-if="!clubId && !branchId" class="attachment-toggle" role="group" aria-label="Sartarosh faoliyati"><button type="button" :aria-pressed="!linked" :disabled="saving" @click="setLinked(false)">Mustaqil</button><button type="button" :aria-pressed="linked" :disabled="saving" @click="setLinked(true)">Sartaroshxonada</button></div>
              <template v-if="linked">
                <div class="form-group"><label>Sartaroshxona <span>*</span></label><RemoteSelect :key="`salon-${session}`" :model-value="selectedSalon" :fetch-options="searchSalons" label="Sartaroshxona" placeholder="Sartaroshxonani qidirish…" :disabled="saving || Boolean(clubId || branchId)" @update:model-value="chooseSalon" /></div>
                <div class="form-group"><label>Filial <span>*</span></label><RemoteSelect :key="`branch-${session}-${selectedSalon?.value || ''}`" :model-value="selectedBranch" :fetch-options="searchBranches" label="Filial" placeholder="Filialni qidirish…" :disabled="saving || !selectedSalon || Boolean(branchId)" @update:model-value="chooseBranch" /></div>
              </template>
              <div v-else class="field-grid"><div class="form-group"><label for="barber-city">Shahar <span>*</span></label><select id="barber-city" v-model="form.billing_city" required :disabled="saving" @change="form.billing_district = ''"><option value="" disabled>Tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option></select></div><div class="form-group"><label for="barber-district">Tuman <span>*</span></label><select id="barber-district" v-model="form.billing_district" required :disabled="saving || isDistrictLoading || !form.billing_city"><option value="" disabled>{{ isDistrictLoading ? 'Yuklanmoqda…' : 'Tanlang' }}</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option></select><small v-if="districtError" role="alert">{{ districtError }}</small></div></div>
              <div class="field-grid compact-grid"><div class="form-group"><label for="barber-latitude">Latitude <span>*</span></label><input id="barber-latitude" v-model.number="form.latitude" type="number" inputmode="decimal" min="-90" max="90" step="0.000001" required placeholder="41.311081" :disabled="saving"></div><div class="form-group"><label for="barber-longitude">Longitude <span>*</span></label><input id="barber-longitude" v-model.number="form.longitude" type="number" inputmode="decimal" min="-180" max="180" step="0.000001" required placeholder="69.240562" :disabled="saving"></div></div>
              <div class="field-grid compact-grid schedule-row"><div class="form-group"><label for="barber-work-start">Ish boshlanishi <span>*</span></label><input id="barber-work-start" v-model="form.work_start_time" type="time" required :disabled="saving"></div><div class="form-group"><label for="barber-work-end">Ish tugashi <span>*</span></label><input id="barber-work-end" v-model="form.work_end_time" type="time" required :disabled="saving"></div></div>
            </template>
          </div>
          <footer class="barber-dialog-footer"><button type="button" class="cancel-button" :disabled="saving" @click="close">Bekor qilish</button><button type="submit" class="primary-button" :disabled="saving || loading || (!linked && isDistrictLoading)">{{ saving ? 'Saqlanmoqda…' : 'Qo‘shish' }}</button></footer>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.barber-dialog .barber-dialog-card { width: min(100%, 620px); max-height: calc(100dvh - 32px); display: flex; flex-direction: column; padding: 0; overflow: hidden; border: 1px solid var(--panel-border); border-radius: 20px; background: var(--surface); }
.barber-dialog-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 20px 24px; border-bottom: 1px solid var(--panel-border); flex-shrink: 0; }.barber-dialog-header h2 { margin: 0; font-size: 20px; letter-spacing: -.03em; font-weight: 750; }
.close-button { display: grid; place-items: center; flex-shrink: 0; width: 34px; height: 34px; padding: 0; border: 0; border-radius: 9px; background: var(--control); color: var(--muted); cursor: pointer; }
.barber-form { display: flex; flex-direction: column; min-height: 0; }.barber-dialog-body { display: grid; gap: 18px; padding: 24px; overflow-y: auto; min-height: 0; }
.form-group { display: grid; gap: 7px; align-content: start; min-width: 0; }.form-group > label { color: var(--muted); font-size: 12px; font-weight: 600; }.form-group > label span { color: var(--accent); }
.form-group > input, .form-group > select { width: 100%; min-width: 0; min-height: 44px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--control); color: var(--text); font: inherit; font-size: 13px; }.form-group > input:focus, .form-group > select:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent); }.form-group > :disabled { opacity: .55; }.form-group > small { color: var(--danger); font-size: 11px; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; min-width: 0; }.schedule-row { padding-top: 16px; border-top: 1px solid var(--panel-border); }
.attachment-toggle { display: flex; gap: 4px; padding: 4px; border: 1px solid var(--border); border-radius: 11px; background: var(--control); }.attachment-toggle button { flex: 1; min-height: 36px; padding: 8px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); font: inherit; font-size: 12px; cursor: pointer; }.attachment-toggle button[aria-pressed="true"] { background: var(--surface); color: var(--accent); box-shadow: 0 1px 4px #0f172a10; }
.barber-dialog-footer { display: flex; justify-content: flex-end; align-items: center; gap: 20px; padding: 16px 24px; border-top: 1px solid var(--panel-border); flex-shrink: 0; }.cancel-button { border: 0; background: transparent; color: var(--muted); font: inherit; font-size: 13px; cursor: pointer; }.barber-dialog-footer .primary-button { min-width: 130px; min-height: 42px; border-radius: 10px; font-size: 13px; }
.form-error { margin: 0; padding: 12px; border: 1px solid var(--border); border-radius: 10px; color: var(--danger); background: var(--danger-soft); font-size: 12px; }.loading-state { margin: 0; padding: 24px; text-align: center; color: var(--muted); font-size: 13px; }
@media (max-width: 600px) { .barber-dialog { padding: 10px; }.barber-dialog-card { max-height: calc(100dvh - 20px); border-radius: 16px; }.barber-dialog-header { padding: 18px; }.barber-dialog-header h2 { font-size: 18px; }.barber-dialog-body { padding: 18px; gap: 16px; }.field-grid { grid-template-columns: 1fr; }.compact-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }.form-group > input, .form-group > select { font-size: 16px; }.barber-dialog-footer { padding: 14px 18px; } }
</style>
