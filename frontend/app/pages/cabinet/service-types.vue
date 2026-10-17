<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
import type { ServiceTypeManagementItem } from "~/api/serviceTypes"
import { descendantServiceIds, serviceTreeOptions } from "~/utils/serviceTree"

definePageMeta({ alias: ["/site/staff/panel/service-types"], layout: "admin", middleware: ["admin"] })
useHead({ title: "Xizmat turlari" })
const api = useAdminApi()
const { user } = useAuth()
const isSuperuser = computed(() => Boolean(user.value?.is_superuser))
const cabinetPath = useCabinetPath()
if (!isSuperuser.value) await navigateTo(cabinetPath())
const services = ref<ServiceTypeManagementItem[]>([])
const error = ref("")
const saving = ref(false)
const formOpen = ref(false)
const editingId = ref<string | null>(null)
const emptyForm = () => ({ code: "", name: "", name_ru: "", name_en: "", parent: null as string | null, is_active: false, sort_order: 0 })
const form = ref(emptyForm())
const rows = computed(() => serviceTreeOptions(services.value))
const searchQuery = ref("")
const filteredRows = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase()
  return rows.value.filter(service => [service.name, service.name_ru, service.name_en, service.code].some(value => value?.toLocaleLowerCase().includes(query)))
})
const parentChoices = computed(() => {
  const excluded = editingId.value ? descendantServiceIds(services.value, [editingId.value]) : new Set<string>()
  return rows.value.filter(service => !excluded.has(service.id))
})
const reload = async () => {
  services.value = await api.getServiceTypes()
  await refreshNuxtData("cabinet-navigation-service-types")
}
const edit = (service?: ServiceTypeManagementItem) => {
  editingId.value = service?.id || null
  form.value = service ? { code: service.code, name: service.name, name_ru: service.name_ru, name_en: service.name_en, parent: service.parent || null, is_active: service.is_active, sort_order: service.sort_order } : emptyForm()
  error.value = ""
  formOpen.value = true
}
const save = async () => {
  saving.value = true
  error.value = ""
  try {
    if (editingId.value) await api.updateServiceType(editingId.value, form.value)
    else await api.createServiceType(form.value)
    await reload()
    formOpen.value = false
    useToast().success("Saqlandi.")
  } catch (err) { error.value = cabinetErrorMessage(err) }
  finally { saving.value = false }
}
const remove = async (service: ServiceTypeManagementItem) => {
  if (!window.confirm(`${service.name} xizmatini o‘chirishni tasdiqlaysizmi?`)) return
  try { await api.deleteServiceType(service.id); await reload() }
  catch (err) { error.value = cabinetErrorMessage(err) }
}
onMounted(() => reload().catch(err => { error.value = cabinetErrorMessage(err) }))
</script>

<template>
  <div class="service-management">
    <div class="filter-bar cabinet-list-toolbar">
      <div class="search-wrap"><input v-model="searchQuery" type="search" aria-label="Xizmat turi" placeholder="Xizmat nomi yoki kodi..." class="service-search"></div>
      <button class="primary-button" type="button" @click="edit()"><CabinetIcon name="plus" /> Xizmat qo‘shish</button>
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <form v-if="formOpen" class="service-form" @submit.prevent="save">
      <div class="service-form-grid">
        <label>Kod<input v-model="form.code" required maxlength="50" pattern="[A-Za-z0-9_-]+" :disabled="saving || Boolean(editingId)"></label>
        <label>Asosiy xizmat<select v-model="form.parent" :disabled="saving"><option :value="null">Asosiy bo‘lim</option><option v-for="service in parentChoices" :key="service.id" :value="service.id">{{ service.label }}</option></select></label>
        <label>O‘zbekcha nom<input v-model="form.name" required maxlength="100" :disabled="saving"></label>
        <label>Ruscha nom<input v-model="form.name_ru" required maxlength="100" :disabled="saving"></label>
        <label>Inglizcha nom<input v-model="form.name_en" required maxlength="100" :disabled="saving"></label>
        <label>Tartib<input v-model.number="form.sort_order" type="number" min="0" max="32767" :disabled="saving"></label>
      </div>
      <label class="service-active"><input v-model="form.is_active" type="checkbox" :disabled="saving">Faol</label>
      <div class="service-form-actions"><button class="secondary-button" type="button" :disabled="saving" @click="formOpen = false">Bekor qilish</button><button class="primary-button" :disabled="saving">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button></div>
    </form>
    <div class="service-table-wrap"><table class="service-table"><thead><tr><th>Nomi</th><th>Kod</th><th>Tartib</th><th>Holat</th><th>Amallar</th></tr></thead><tbody>
      <tr v-for="service in filteredRows" :key="service.id"><td><span :style="{ paddingLeft: `${service.depth * 18}px` }">{{ service.depth ? '↳ ' : '' }}{{ service.name }}</span></td><td>{{ service.code }}</td><td>{{ service.sort_order }}</td><td>{{ service.is_active ? 'Faol' : 'Faol emas' }}</td><td class="service-row-actions"><button class="secondary-button" type="button" @click="edit(service)">Tahrirlash</button><button class="secondary-button" type="button" @click="remove(service)">O‘chirish</button></td></tr>
      <tr v-if="!filteredRows.length"><td colspan="5">{{ searchQuery.trim() ? 'Xizmat turlari topilmadi.' : 'Xizmat turlari hali qo‘shilmagan.' }}</td></tr>
    </tbody></table></div>
  </div>
</template>

<style scoped>
.service-management { display: grid; gap: 16px; }
.service-search { width: 100%; }
.service-form { padding: 18px; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; display: grid; gap: 14px; }
.service-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.service-form-grid label { display: grid; gap: 6px; font-size: 13px; font-weight: 650; }
.service-form input:not([type=checkbox]), .service-form select { width: 100%; min-height: 42px; border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; background: var(--control); color: var(--text); }
.service-active { display: flex; gap: 8px; align-items: center; }
.service-form-actions { display: flex; gap: 8px; justify-content: flex-end; }
.service-table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 14px; }
.service-table { width: 100%; border-collapse: collapse; background: var(--surface); font-size: 13px; }
.service-table td, .service-table th { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
.service-row-actions { display: flex; gap: 8px; }
@media (max-width: 640px) { .service-form-grid { grid-template-columns: 1fr; } }
</style>
