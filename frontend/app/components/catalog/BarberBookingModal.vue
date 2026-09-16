<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCircleCheck } from "@fortawesome/free-solid-svg-icons"
import { useBarbersApi } from "~/api/barbers"
import { useAuth } from "~/composables/useAuth"
import type { BarberAvailability, BarberItem, BarberSlot } from "~/types/barber"

const props = defineProps<{
  barber: BarberItem | null
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void
  (e: "booked", booking: any): void
}>()

const barbersApi = useBarbersApi()
const auth = useAuth()
const { t } = useTranslations()

const selectedDate = ref("")
const availability = ref<BarberAvailability | null>(null)
const selectedSlot = ref<BarberSlot | null>(null)
const isLoadingSlots = ref(false)
const isBooking = ref(false)
const errorMessage = ref("")
const successBooking = ref<any>(null)

// Initialize with today's date in YYYY-MM-DD
const initDate = () => {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  selectedDate.value = `${year}-${month}-${day}`
}

const minDate = computed(() => {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
})

const maxDate = computed(() => {
  const d = new Date()
  d.setDate(d.getDate() + 14)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
})

const displayBranch = computed(() => {
  if (!props.barber?.branch_name) return ""
  const parts = props.barber.branch_name.split(/[-—]/).map(s => s.trim())
  return parts.length > 1 ? (parts[parts.length - 1] || "") : props.barber.branch_name
})

const fetchSlots = async () => {
  if (!props.barber || !selectedDate.value) return
  isLoadingSlots.value = true
  errorMessage.value = ""
  selectedSlot.value = null
  try {
    const res = await barbersApi.getAvailability(props.barber.id, selectedDate.value)
    availability.value = res
  } catch (err: any) {
    errorMessage.value = err?.message || t("barbers.slots_load_error")
  } finally {
    isLoadingSlots.value = false
  }
}

watch(
  () => props.modelValue,
  (val) => {
    if (val && props.barber) {
      initDate()
      successBooking.value = null
      fetchSlots()
    }
  },
)

watch(selectedDate, () => {
  if (props.modelValue && props.barber) {
    fetchSlots()
  }
})

const handleSlotSelect = (slot: BarberSlot) => {
  if (!slot.is_available) return
  selectedSlot.value = slot
}

const handleConfirmBooking = async () => {
  if (!props.barber || !selectedSlot.value) return
  const toast = useToast()
  if (!auth.isAuthenticated.value) {
    const authMsg = t("barbers.auth_required_to_book")
    errorMessage.value = authMsg
    toast.warning(authMsg)
    return
  }

  isBooking.value = true
  errorMessage.value = ""
  try {
    const booking = await barbersApi.bookBarber(
      props.barber.id,
      selectedSlot.value.starts_at,
      selectedSlot.value.ends_at,
    )
    successBooking.value = booking
    toast.success(t("barbers.booking_success_title"))
    emit("booked", booking)
  } catch (err: any) {
    const errText = err?.message || t("barbers.booking_error_slot_taken")
    errorMessage.value = errText
    toast.error(errText)
  } finally {
    isBooking.value = false
  }
}

const closeModal = () => {
  emit("update:modelValue", false)
}
</script>

<template>
  <div v-if="modelValue && barber" class="modal-backdrop" @click.self="closeModal">
    <div class="modal-card">
      <button class="modal-close-btn" @click="closeModal">✕</button>

      <!-- Success Screen -->
      <div v-if="successBooking" class="success-screen">
        <FontAwesomeIcon :icon="faCircleCheck" class="success-check-icon" />
        <h2>{{ t("barbers.booking_success_title") }}</h2>
        <p class="success-desc">
          {{ t("barbers.booking_success_desc", { name: barber.full_name }) }}
        </p>

        <div class="booking-receipt-card">
          <div class="receipt-row">
            <span>{{ t("barbers.venue") }}:</span>
            <strong>{{ barber.club_name }}</strong>
          </div>
          <div class="receipt-row">
            <span>{{ t("barbers.branch") }}:</span>
            <span>{{ barber.branch_name || t("barbers.main_branch") }}</span>
          </div>
          <div class="receipt-row">
            <span>{{ t("barbers.date_and_time") }}:</span>
            <strong class="receipt-time">{{ selectedDate }} | {{ selectedSlot?.time_label }}</strong>
          </div>
          <div class="receipt-row">
            <span>{{ t("barbers.payment_type") }}:</span>
            <span class="pay-note">{{ t("barbers.pay_on_site") }}</span>
          </div>
        </div>

        <div class="success-actions">
          <NuxtLink to="/bookings" class="btn btn-primary" @click="closeModal">
            {{ t("bookings.view_my_bookings") }}
          </NuxtLink>
          <button class="btn btn-outline" @click="closeModal">
            {{ t("common.close") }}
          </button>
        </div>
      </div>

      <!-- Booking Form -->
      <div v-else class="booking-form-content">
        <!-- Clean Compact Header without circular avatar placeholder -->
        <div class="barber-header-summary">
          <h3 class="barber-name">{{ barber.full_name }}</h3>
          <p class="salon-name">{{ barber.club_name }}<span v-if="displayBranch"> ({{ displayBranch }})</span></p>
          <div class="status-indicator">
            <span class="dot" :class="barber.status.toLowerCase()" />
            <small>{{ t("barbers.status_" + (barber.status?.toLowerCase() || "available")) }}</small>
          </div>
        </div>

        <div v-if="errorMessage" class="alert alert-error">
          {{ errorMessage }}
        </div>

        <!-- 1. Select Date -->
        <div class="form-section">
          <label class="section-label">{{ t("barbers.select_date") }}:</label>
          <input
            v-model="selectedDate"
            type="date"
            class="date-input"
            :min="minDate"
            :max="maxDate"
          >
        </div>

        <!-- 2. Select 1-Hour Slot -->
        <div class="form-section">
          <div v-if="isLoadingSlots" class="slots-loading">
            <div class="spinner-sm" />
            <span>{{ t("barbers.slots_loading") }}</span>
          </div>

          <div v-else-if="!availability?.is_available" class="not-available-box">
            <p>{{ availability?.reason || t("barbers.not_accepting_today") }}</p>
          </div>

          <div v-else-if="availability.slots.length === 0" class="empty-slots">
            {{ t("barbers.no_slots_today") }}
          </div>

          <div v-else class="slots-grid">
            <button
              v-for="slot in availability.slots"
              :key="slot.hour"
              type="button"
              class="slot-chip"
              :class="{
                'available': slot.is_available,
                'occupied': !slot.is_available,
                'selected': selectedSlot?.hour === slot.hour
              }"
              :disabled="!slot.is_available"
              @click="handleSlotSelect(slot)"
            >
              <span class="slot-time">{{ slot.time_label }}</span>
              <span v-if="!slot.is_available" class="slot-status">
                {{ slot.is_past ? t("barbers.slot_past") : t("barbers.slot_taken") }}
              </span>
            </button>
          </div>
        </div>

        <!-- Price notice banner -->
        <div class="price-info-card">
          <strong>{{ t("barbers.price_negotiated_on_site") }}</strong>
          <p>{{ t("barbers.price_info_text") }}</p>
        </div>

        <!-- Submit Button -->
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-primary btn-block"
            :disabled="!selectedSlot || isBooking"
            @click="handleConfirmBooking"
          >
            <span v-if="isBooking">{{ t("bookings.in_progress") }}</span>
            <span v-else-if="selectedSlot">{{ t("barbers.book_for_time_btn", { time: selectedSlot.time_label }) }}</span>
            <span v-else>{{ t("barbers.select_time") }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(3, 9, 20, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.modal-card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  max-width: 440px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  padding: 1.4rem;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4);
  color: var(--text);
}

.modal-close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: var(--control, rgba(255, 255, 255, 0.06));
  border: 1px solid var(--border);
  border-radius: 50%;
  width: 30px;
  height: 30px;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.modal-close-btn:hover {
  background: var(--border);
}

.barber-header-summary {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 1.1rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--border);
  padding-right: 30px;
}

.barber-name {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text);
}

.salon-name {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--muted);
  margin-top: 3px;
  font-size: 0.8rem;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot.available { background: #22c55e; }
.dot.break { background: #eab308; }
.dot.not_at_work { background: #f97316; }
.dot.day_off { background: #ef4444; }

.form-section {
  margin-bottom: 1rem;
}

.section-label {
  display: block;
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 0.4rem;
  color: var(--text);
}

.date-input {
  width: 100%;
  padding: 0.6rem 0.8rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--control, rgba(255, 255, 255, 0.04));
  color: var(--text);
  font-size: 0.9rem;
  outline: none;
}

.date-input:focus {
  border-color: var(--accent);
}

.slots-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.slot-chip {
  padding: 0.55rem 0.4rem;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--control, rgba(255, 255, 255, 0.04));
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  transition: all 0.15s ease;
  color: var(--text);
}

.slot-chip.available:hover {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.08);
}

.slot-chip.selected {
  background: #10b981 !important;
  border-color: #10b981 !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
}

.slot-chip.occupied {
  opacity: 0.4;
  cursor: not-allowed;
  background: rgba(0, 0, 0, 0.15);
}

.slot-time {
  font-weight: 750;
  font-size: 0.82rem;
}

.slot-status {
  font-size: 0.68rem;
  opacity: 0.75;
}

.slots-loading,
.not-available-box,
.empty-slots {
  padding: 0.75rem;
  text-align: center;
  border-radius: 8px;
  background: var(--control, rgba(255, 255, 255, 0.04));
  font-size: 0.85rem;
  color: var(--muted);
}

.price-info-card {
  background: var(--control, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  margin-bottom: 1rem;
  font-size: 0.82rem;
}

.price-info-card strong {
  display: block;
  font-size: 0.85rem;
  font-weight: 700;
  margin-bottom: 2px;
}

.price-info-card p {
  margin: 0;
  font-size: 0.75rem;
  color: var(--muted);
  line-height: 1.35;
}

.modal-footer {
  margin-top: 0.75rem;
}

.btn-block {
  width: 100%;
}

.btn {
  padding: 0.75rem 1.25rem;
  border-radius: 10px;
  font-weight: 750;
  cursor: pointer;
  border: none;
  font-size: 0.92rem;
  text-align: center;
  text-decoration: none;
  transition: all 0.15s ease;
}

.btn-primary {
  background: #10b981;
  color: white;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.25);
}

.btn-primary:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.35);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}

.btn-outline:hover {
  background: var(--control);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  background: var(--border);
  color: var(--muted);
  box-shadow: none;
}

.alert {
  padding: 0.65rem 0.85rem;
  border-radius: 8px;
  margin-bottom: 0.85rem;
  font-size: 0.82rem;
}

.alert-error {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.success-screen {
  text-align: center;
  padding: 0.75rem 0;
}

.success-check-icon {
  font-size: 2.5rem;
  color: #10b981;
  margin-bottom: 0.5rem;
}

.success-screen h2 {
  font-size: 1.15rem;
  margin: 0 0 0.4rem;
}

.success-desc {
  font-size: 0.85rem;
  color: var(--muted);
  margin: 0;
}

.booking-receipt-card {
  background: var(--control, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.85rem 1rem;
  margin: 1.25rem 0;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.receipt-row {
  display: flex;
  justify-content: space-between;
}

.receipt-time {
  color: var(--accent);
}

.pay-note {
  color: #34d399;
  font-weight: 600;
}

.success-actions {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.spinner-sm {
  width: 18px;
  height: 18px;
  border: 2px solid #10b981;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  display: inline-block;
  vertical-align: middle;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 600px) {
  .modal-backdrop {
    align-items: flex-end;
    padding: 0;
  }

  .modal-card {
    border-radius: 20px 20px 0 0;
    max-height: 88vh;
    padding: 1.25rem 1rem calc(1.25rem + env(safe-area-inset-bottom, 0px));
    width: 100%;
    animation: slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>
