<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
const props = defineProps<{ kind: "booking" | "barber" }>()
const emit = defineEmits<{ saved: [] }>()
const { user } = useAuth()
const isStaff = computed(() => user.value?.is_staff || user.value?.is_superuser || ["ADMIN", "MODERATOR"].includes(user.value?.role || ""))
const api = useAdminApi()
const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref("")
const customers = ref<any[]>([])
const resources = ref<any[]>([])
const cities = ref<any[]>([])
const form = ref({ user: "", resource: "", full_name: "", phone: "", starts_at: "", ends_at: "", quantity: 1, billing_city: "", billing_district: "" })
const { districts, isDistrictLoading, districtError } = useCityDistricts(() => form.value.billing_city)
const title = computed(() => props.kind === "booking" ? "Bron qo‘shish" : "Sartarosh qo‘shish")
const dialogId = computed(() => `operator-${props.kind}-dialog`)
const close = () => { if (!saving.value) open.value = false }
useDialogFocus(open, `#operator-${props.kind}-dialog`, close)
const allPages = async (fetcher: (params: Record<string, any>) => Promise<any>, params: Record<string, any>) => {
  const items: any[] = []; let page = 1; let next = true
  while (next) { const response = await fetcher({ ...params, page: page++, page_size: 100 }); items.push(...response.results); next = Boolean(response.next) }
  return items
}
const begin = async () => {
  open.value = true; loading.value = true; error.value = ""
  form.value = { user: "", resource: "", full_name: "", phone: "", starts_at: "", ends_at: "", quantity: 1, billing_city: "", billing_district: "" }
  try {
    const results = await Promise.all([
      allPages(api.getUsers, { ...(props.kind === "booking" ? { role: "CUSTOMER" } : {}), status: "ACTIVE" }),
      allPages(props.kind === "booking" ? api.getZones : api.getBranches, {}),
    ])
    customers.value = results[0].filter(account => ["CUSTOMER", "CLIENT"].includes(account.role))
    resources.value = results[1]
    if (props.kind === "barber") {
      cities.value = await api.getCities()
      const clubs = await allPages(api.getClubs, { category: "BARBERSHOP" })
      const ids = new Set(clubs.map(club => club.id))
      resources.value = resources.value.filter(branch => ids.has(typeof branch.club === "string" ? branch.club : branch.club?.id))
    }
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally { loading.value = false }
}
const save = async () => {
  if (saving.value) return
  saving.value = true; error.value = ""
  try {
    if (props.kind === "booking") {
      await api.createBooking({ user: form.value.user, zone: form.value.resource, starts_at: new Date(form.value.starts_at).toISOString(), ends_at: new Date(form.value.ends_at).toISOString(), quantity: form.value.quantity })
    } else {
      const branch = resources.value.find(item => item.id === form.value.resource)
      await api.createBarber({ user: form.value.user, branch: branch?.id || null, club: branch ? (typeof branch.club === "string" ? branch.club : branch.club.id) : null, billing_city: branch ? null : form.value.billing_city || null, billing_district: branch ? null : form.value.billing_district || null, full_name: form.value.full_name, phone: form.value.phone, affiliation_status: "APPROVED", working_days: [1, 2, 3, 4, 5, 6, 7] })
    }
    open.value = false; emit("saved"); useToast().success("Saqlandi.")
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally { saving.value = false }
}
</script>
<template>
  <button v-if="isStaff" type="button" class="primary-button" @click="begin"><CabinetIcon name="plus" />{{ title }}</button>
  <Teleport to="body">
    <div v-if="open" :id="dialogId" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" :aria-labelledby="`${dialogId}-title`" tabindex="-1" @click.self="close">
      <div class="modal-card"><div class="modal-header"><h2 :id="`${dialogId}-title`">{{ title }}</h2><button type="button" class="modal-close-btn" aria-label="Yopish" :disabled="saving" @click="close"><CabinetIcon name="close" /></button></div>
        <form class="modal-form" @submit.prevent="save">
          <p v-if="error" class="form-error" role="alert">{{ error }}</p><p v-if="loading">Yuklanmoqda…</p>
          <template v-else>
            <div class="form-group"><label :for="`${dialogId}-user`">{{ kind === 'booking' ? 'Bron egasi' : 'Akkaunt' }}</label><select :id="`${dialogId}-user`" v-model="form.user" required :disabled="saving"><option value="" disabled>Tanlang</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.profile?.full_name || customer.username }} — {{ customer.phone }}</option></select></div>
            <div class="form-group"><label :for="`${dialogId}-resource`">{{ kind === 'booking' ? 'Resurs' : 'Filial' }}</label><select :id="`${dialogId}-resource`" v-model="form.resource" :required="kind === 'booking'" :disabled="saving"><option value="" :disabled="kind === 'booking'">{{ kind === 'barber' ? 'Mustaqil sartarosh' : 'Tanlang' }}</option><option v-for="resource in resources" :key="resource.id" :value="resource.id">{{ resource.branch_name || resource.club_name }} — {{ resource.name }}</option></select></div>
            <template v-if="kind === 'booking'"><div class="form-group"><label :for="`${dialogId}-start`">Boshlanish</label><input :id="`${dialogId}-start`" v-model="form.starts_at" type="datetime-local" required :disabled="saving"></div><div class="form-group"><label :for="`${dialogId}-end`">Tugash</label><input :id="`${dialogId}-end`" v-model="form.ends_at" type="datetime-local" required :disabled="saving"></div><div class="form-group"><label :for="`${dialogId}-quantity`">Soni</label><input :id="`${dialogId}-quantity`" v-model.number="form.quantity" type="number" min="1" step="1" required :disabled="saving"></div></template>
            <template v-else><div v-if="!form.resource" class="form-group"><label :for="`${dialogId}-city`">Shahar</label><select :id="`${dialogId}-city`" v-model="form.billing_city" required :disabled="saving" @change="form.billing_district = ''"><option value="" disabled>Tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option></select></div><div v-if="!form.resource" class="form-group"><label :for="`${dialogId}-district`">Tuman</label><select :id="`${dialogId}-district`" v-model="form.billing_district" required :disabled="saving || isDistrictLoading || !form.billing_city"><option value="" disabled>{{ isDistrictLoading ? 'Yuklanmoqda…' : 'Tumanni tanlang' }}</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option></select><small v-if="districtError" role="alert">{{ districtError }}</small><small v-else-if="form.billing_city && !isDistrictLoading && !districts.length">Bu hudud uchun tumanlar hali qo‘shilmagan.</small></div><div class="form-group"><label :for="`${dialogId}-name`">Ism-familiya</label><input :id="`${dialogId}-name`" v-model="form.full_name" maxlength="180" required :disabled="saving"></div><div class="form-group"><label :for="`${dialogId}-phone`">Telefon</label><input :id="`${dialogId}-phone`" v-model="form.phone" type="tel" :disabled="saving"></div></template>
          </template>
          <div class="modal-actions"><button type="button" class="secondary-button" :disabled="saving" @click="close">Bekor qilish</button><button type="submit" class="primary-button" :disabled="saving || loading || (kind === 'barber' && !form.resource && isDistrictLoading)">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button></div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
