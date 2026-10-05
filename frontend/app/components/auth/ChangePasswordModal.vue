<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faKey, faXmark, faEye, faEyeSlash, faCircleCheck } from "@fortawesome/free-solid-svg-icons"
import { useAuth } from "~/composables/useAuth"
import { useTranslations } from "~/composables/useTranslations"
import { ApiRequestError } from "~/types/api"

const props = withDefaults(defineProps<{ modelValue: boolean; force?: boolean; title?: string; description?: string }>(), { force: false, title: "", description: "" })
const emit = defineEmits<{ (event: "update:modelValue", value: boolean): void; (event: "success" | "close"): void }>()
const { changePassword } = useAuth()
const { t } = useTranslations()
const oldPassword = ref("")
const newPassword = ref("")
const confirmPassword = ref("")
const visiblePasswords = ref(false)
const isLoading = ref(false)
const errorMessage = ref("")
const successMessage = ref("")
const open = computed(() => props.modelValue)
const close = () => { if (!props.force && !isLoading.value) { emit("update:modelValue", false); emit("close") } }
useDialogFocus(open, "#change-password-dialog", close)
watch(open, (value) => { if (value) { oldPassword.value = ""; newPassword.value = ""; confirmPassword.value = ""; visiblePasswords.value = false; errorMessage.value = ""; successMessage.value = "" } })
const onSubmit = async () => {
  if (isLoading.value) return
  errorMessage.value = ""
  if (newPassword.value !== confirmPassword.value) { errorMessage.value = "Yangi parollar mos kelmadi."; return }
  if (newPassword.value === oldPassword.value) { errorMessage.value = "Yangi parol joriy paroldan farq qilishi kerak."; return }
  isLoading.value = true
  try {
    await changePassword({ old_password: oldPassword.value, new_password: newPassword.value, confirm_password: confirmPassword.value })
    oldPassword.value = ""; newPassword.value = ""; confirmPassword.value = ""
    emit("success"); emit("update:modelValue", false)
    useToast().success("Parol yangilandi")
  } catch (error) {
    const code = error instanceof ApiRequestError ? error.code : ""
    errorMessage.value = code === "auth.invalid_old_password" ? "Joriy parol noto‘g‘ri." : code && t(code) !== code ? t(code) : "Parolni yangilab bo‘lmadi. Qayta urinib ko‘ring."
  } finally { isLoading.value = false }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" id="change-password-dialog" class="password-backdrop cabinet-modal" role="dialog" aria-modal="true" aria-labelledby="password-dialog-title" tabindex="-1" @click.self="close">
      <div class="password-card">
        <div class="password-header"><span class="password-icon"><FontAwesomeIcon :icon="faKey" /></span><button v-if="!force" type="button" class="password-close" aria-label="Oynani yopish" :disabled="isLoading" @click="close"><FontAwesomeIcon :icon="faXmark" /></button></div>
        <h2 id="password-dialog-title">{{ title || 'Parolni yangilash' }}</h2>
        <p v-if="force || description" class="password-description">{{ force ? 'Davom etish uchun yangi parol o‘rnating.' : description }}</p>
        <p v-if="errorMessage" class="password-error" role="alert">{{ errorMessage }}</p>
        <p v-if="successMessage" role="status"><FontAwesomeIcon :icon="faCircleCheck" />{{ successMessage }}</p>
        <form class="password-form" @submit.prevent="onSubmit">
          <div><label for="change-old-password">Joriy parol</label><input id="change-old-password" v-model="oldPassword" :type="visiblePasswords ? 'text' : 'password'" autocomplete="current-password" required :disabled="isLoading"></div>
          <div><label for="change-new-password">Yangi parol</label><input id="change-new-password" v-model="newPassword" :type="visiblePasswords ? 'text' : 'password'" autocomplete="new-password" placeholder="Kamida 6 ta belgi" minlength="6" required :disabled="isLoading"></div>
          <div><label for="change-confirm-password">Yangi parolni tasdiqlang</label><input id="change-confirm-password" v-model="confirmPassword" :type="visiblePasswords ? 'text' : 'password'" autocomplete="new-password" minlength="6" required :disabled="isLoading"></div>
          <button type="button" class="password-visibility" :aria-pressed="visiblePasswords" @click="visiblePasswords = !visiblePasswords"><FontAwesomeIcon :icon="visiblePasswords ? faEyeSlash : faEye" />{{ visiblePasswords ? 'Parollarni yashirish' : 'Parollarni ko‘rsatish' }}</button>
          <button type="submit" class="password-submit" :disabled="isLoading">{{ isLoading ? 'Saqlanmoqda…' : 'Parolni saqlash' }}</button>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.password-backdrop { position: fixed; inset: 0; z-index: 110; display: grid; place-items: center; background: #0b122980; backdrop-filter: blur(4px); padding: 16px; }
.password-card { width: min(100%, 420px); max-height: calc(100dvh - 32px); overflow-y: auto; border-radius: 16px; padding: 28px; background: var(--surface); color: var(--text); border: 1px solid var(--panel-border); box-shadow: var(--cabinet-shadow); }
.password-header { display: flex; align-items: center; justify-content: space-between; }
.password-icon { display: grid; place-items: center; width: 40px; height: 40px; border-radius: 11px; background: var(--accent-soft); color: var(--accent); }
.password-close { border: 0; border-radius: 8px; width: 40px; height: 40px; background: var(--control); color: var(--muted); cursor: pointer; }
h2 { margin: 20px 0; font-size: 21px; letter-spacing: -.5px; font-weight: 650; }
.password-description { font-size: 12px; color: var(--muted); line-height: 1.6; margin: -8px 0 20px; }
.password-form { display: flex; flex-direction: column; gap: 16px; }
.password-form label { display: block; margin-bottom: 8px; font-size: 12px; font-weight: 600; }
.password-form input { width: 100%; }
.password-visibility { display: flex; align-items: center; gap: 8px; border: 0; background: transparent; color: var(--muted); font-size: 11px; cursor: pointer; min-height: 36px; padding: 0; }
.password-submit { min-height: 44px; padding: 12px; background: var(--accent); color: var(--accent-text); border: 0; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; }
.password-submit:disabled { opacity: .5; cursor: wait; }
.password-error { margin: 0 0 16px; padding: 12px; font-size: 12px; line-height: 1.5; border-radius: 8px; color: var(--danger); background: var(--danger-soft); }
@media (max-width: 600px) { .password-card { padding: 22px 18px; } }
</style>
