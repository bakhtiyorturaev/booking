<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
import type { CabinetBarberItem } from "~/types/barber"

const props = defineProps<{ barber: CabinetBarberItem }>()
const emit = defineEmits<{ saved: [] }>()
const api = useAdminApi()
const open = ref(false)
const saving = ref(false)
const error = ref("")
const form = ref({ full_name: "", phone: "", status: "AVAILABLE", work_start_time: "09:00", work_end_time: "20:00", working_days: [] as number[] })
const dialogId = `barber-schedule-${props.barber.id}`
const close = () => { if (!saving.value) open.value = false }
useDialogFocus(open, `#${dialogId}`, close)
const begin = () => {
  const barber = props.barber
  form.value = { full_name: barber.full_name, phone: barber.phone, status: barber.status, work_start_time: barber.work_start_time.slice(0, 5), work_end_time: barber.work_end_time.slice(0, 5), working_days: [...barber.working_days] }
  error.value = ""
  open.value = true
}
const save = async () => {
  if (saving.value) return
  saving.value = true
  error.value = ""
  try {
    await api.updateBarber(props.barber.id, { ...form.value, working_days: [...form.value.working_days].sort((a, b) => a - b) })
    open.value = false
    emit("saved")
    useToast().success("Saqlandi.")
  } catch (cause) { error.value = cabinetErrorMessage(cause) }
  finally { saving.value = false }
}
const weekdays = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
</script>

<template>
  <button class="btn-sm btn-outline" type="button" @click="begin">Tahrirlash</button>
  <Teleport to="body">
    <div v-if="open" :id="dialogId" class="modal-backdrop cabinet-modal" role="dialog" aria-modal="true" :aria-labelledby="`${dialogId}-title`" tabindex="-1" @click.self="close">
      <div class="modal-card">
        <div class="modal-header"><h2 :id="`${dialogId}-title`">Sartaroshni tahrirlash</h2><button class="modal-close-btn" type="button" aria-label="Yopish" :disabled="saving" @click="close"><CabinetIcon name="close" /></button></div>
        <form class="modal-form" @submit.prevent="save">
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <fieldset class="schedule-fields" :disabled="saving">
            <div class="form-group"><label :for="`${dialogId}-name`">Ism</label><input :id="`${dialogId}-name`" v-model="form.full_name" maxlength="150" required></div>
            <div class="form-group"><label :for="`${dialogId}-phone`">Telefon</label><input :id="`${dialogId}-phone`" v-model="form.phone" type="tel" maxlength="30"></div>
            <div class="form-row"><div class="form-group"><label :for="`${dialogId}-start`">Ish boshlanishi</label><input :id="`${dialogId}-start`" v-model="form.work_start_time" type="time" required></div><div class="form-group"><label :for="`${dialogId}-end`">Ish tugashi</label><input :id="`${dialogId}-end`" v-model="form.work_end_time" type="time" required></div></div>
            <fieldset class="schedule-days"><legend>Ish kunlari</legend><label v-for="(day, index) in weekdays" :key="day"><input v-model="form.working_days" type="checkbox" :value="index + 1">{{ day }}</label></fieldset>
            <div class="form-group"><label :for="`${dialogId}-status`">Ish holati</label><select :id="`${dialogId}-status`" v-model="form.status"><option value="AVAILABLE">Ishlayapti</option><option value="BREAK">Tanaffus</option><option value="NOT_AT_WORK">Ishda emas</option><option value="DAY_OFF">Dam olish kuni</option></select></div>
          </fieldset>
          <div class="modal-actions"><button class="secondary-button" type="button" :disabled="saving" @click="close">Bekor qilish</button><button class="primary-button" type="submit" :disabled="saving">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button></div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.schedule-fields { display: grid; gap: 16px; padding: 0; margin: 0; border: 0; min-width: 0; }
.schedule-days { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; border: 1px solid var(--panel-border); border-radius: 8px; }
.schedule-days legend { font-size: 13px; padding: 0 4px; }
.schedule-days label { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.schedule-days input { width: 16px; height: 16px; }
</style>
