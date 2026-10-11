<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
const emit = defineEmits<{ saved: [] }>()
const { isStaff } = useCabinetAccess()
const api = useAdminApi()
const open = ref(false)
const loading = ref(false)
const saving = ref(false)
const error = ref("")
const customers = ref<any[]>([])
const resources = ref<any[]>([])
const cities = ref<any[]>([])
const form = ref({ user: "", resource: "", full_name: "", phone: "", billing_city: "", billing_district: "" })
const { districts, isDistrictLoading, districtError } = useCityDistricts(() => form.value.billing_city)
const title = "Sartarosh qo‘shish"
const dialogId = "operator-barber-dialog"
const close = () => { if (!saving.value) open.value = false }
useDialogFocus(open, `#${dialogId}`, close)
const allPages = async (fetcher: (params: Record<string, any>) => Promise<any>, params: Record<string, any>) => {
  const items: any[] = []; let page = 1; let next = true
  while (next) { const response = await fetcher({ ...params, page: page++, page_size: 100 }); items.push(...response.results); next = Boolean(response.next) }
  return items
}
const begin = async () => {
  open.value = true; loading.value = true; error.value = ""
  form.value = { user: "", resource: "", full_name: "", phone: "", billing_city: "", billing_district: "" }
  try {
    const results = await Promise.all([
      allPages(api.getUsers, { status: "ACTIVE" }),
      allPages(api.getBranches, {}),
    ])
    customers.value = results[0].filter(account => ["CUSTOMER", "CLIENT"].includes(account.role))
    resources.value = results[1]
    cities.value = await api.getCities()
    const clubs = await allPages(api.getClubs, { category: "BARBERSHOP" })
    const ids = new Set(clubs.map(club => club.id))
    resources.value = resources.value.filter(branch => ids.has(typeof branch.club === "string" ? branch.club : branch.club?.id))
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally { loading.value = false }
}
const save = async () => {
  if (saving.value) return
  saving.value = true; error.value = ""
  try {
    const branch = resources.value.find(item => item.id === form.value.resource)
    await api.createBarber({ user: form.value.user, branch: branch?.id || null, club: branch ? (typeof branch.club === "string" ? branch.club : branch.club.id) : null, billing_city: branch ? null : form.value.billing_city || null, billing_district: branch ? null : form.value.billing_district || null, full_name: form.value.full_name, phone: form.value.phone, affiliation_status: "APPROVED", working_days: [1, 2, 3, 4, 5, 6, 7] })
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
            <div class="form-group"><label :for="`${dialogId}-user`">Akkaunt</label><select :id="`${dialogId}-user`" v-model="form.user" required :disabled="saving"><option value="" disabled>Tanlang</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.profile?.full_name || customer.username }} — {{ customer.phone }}</option></select></div>
            <div class="form-group"><label :for="`${dialogId}-resource`">Filial</label><select :id="`${dialogId}-resource`" v-model="form.resource" :disabled="saving"><option value="">Mustaqil sartarosh</option><option v-for="resource in resources" :key="resource.id" :value="resource.id">{{ resource.branch_name || resource.club_name }} — {{ resource.name }}</option></select></div>
            <div v-if="!form.resource" class="form-group"><label :for="`${dialogId}-city`">Shahar</label><select :id="`${dialogId}-city`" v-model="form.billing_city" required :disabled="saving" @change="form.billing_district = ''"><option value="" disabled>Tanlang</option><option v-for="city in cities" :key="city.id" :value="city.id">{{ city.name }}</option></select></div><div v-if="!form.resource" class="form-group"><label :for="`${dialogId}-district`">Tuman</label><select :id="`${dialogId}-district`" v-model="form.billing_district" required :disabled="saving || isDistrictLoading || !form.billing_city"><option value="" disabled>{{ isDistrictLoading ? 'Yuklanmoqda…' : 'Tumanni tanlang' }}</option><option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option></select><small v-if="districtError" role="alert">{{ districtError }}</small><small v-else-if="form.billing_city && !isDistrictLoading && !districts.length">Bu hudud uchun tumanlar hali qo‘shilmagan.</small></div><div class="form-group"><label :for="`${dialogId}-name`">Ism-familiya</label><input :id="`${dialogId}-name`" v-model="form.full_name" maxlength="180" required :disabled="saving"></div><div class="form-group"><label :for="`${dialogId}-phone`">Telefon</label><input :id="`${dialogId}-phone`" v-model="form.phone" type="tel" :disabled="saving"></div>
          </template>
          <div class="modal-actions"><button type="button" class="secondary-button" :disabled="saving" @click="close">Bekor qilish</button><button type="submit" class="primary-button" :disabled="saving || loading || (!form.resource && isDistrictLoading)">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button></div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
