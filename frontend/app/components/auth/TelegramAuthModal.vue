<script setup lang="ts">
import { useAuthApi } from "~/api/auth"
const props = defineProps<{ modelValue: boolean; title?: string; description?: string }>()
const emit = defineEmits<{ (event: "update:modelValue", value: boolean): void; (event: "authenticated" | "close"): void }>()
const { setUser } = useAuth("customer")
const { locale, t } = useTranslations()
const api = useAuthApi("customer")
const { isTMA, initTMA } = useTelegramWebApp()
const session = ref("")
const deepLink = ref("")
const code = ref("")
const step = ref<"telegram" | "code">("telegram")
const status = ref<"waiting" | "ready" | "expired">("waiting")
const remaining = ref(0)
const loading = ref(false)
const verifying = ref(false)
const error = ref("")
let preparation = 0
let deadline = 0
let polling = false
let pollTimer: ReturnType<typeof setInterval> | undefined
let countdownTimer: ReturnType<typeof setInterval> | undefined
const close = () => { if (!verifying.value) { emit("update:modelValue", false); emit("close") } }
const opened = computed(() => props.modelValue)
useDialogFocus(opened, "#telegram-code-dialog", close)
const stopTimers = () => {
  clearInterval(pollTimer)
  clearInterval(countdownTimer)
}
const tick = () => {
  remaining.value = Math.min(59, Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))
  if (remaining.value === 0) {
    status.value = "expired"
    clearInterval(countdownTimer)
  }
}
const checkStatus = async () => {
  if (polling || !props.modelValue || step.value !== "code" || !session.value || status.value === "expired") return
  const currentSession = session.value
  polling = true
  try {
    const response = await api.telegramCodeStatus(currentSession)
    if (!props.modelValue || session.value !== currentSession) return
    status.value = response.data.status
    if (status.value === "ready") {
      deadline = Date.now() + response.data.expires_in * 1000
      tick()
      clearInterval(pollTimer)
      clearInterval(countdownTimer)
      if (status.value === "ready") countdownTimer = setInterval(tick, 250)
    } else if (status.value === "expired") {
      remaining.value = 0
      stopTimers()
    }
  } catch {
    // Retry while waiting; the server remains authoritative about expiry.
  } finally { polling = false }
}
const prepare = async () => {
  if (loading.value) return
  stopTimers()
  const currentPreparation = ++preparation
  session.value = ""
  loading.value = true; error.value = ""; code.value = ""; deepLink.value = ""
  step.value = "telegram"; status.value = "waiting"; remaining.value = 0
  try {
    if (isTMA.value) {
      await initTMA()
      const { user } = useAuth("customer")
      if (user.value) { emit("authenticated"); emit("update:modelValue", false); return }
      throw new Error("Telegram orqali kirib bo‘lmadi.")
    }
    const response = await api.initTelegramCodeLogin(locale.value)
    if (!props.modelValue || preparation !== currentPreparation) return
    session.value = response.data.session_id
    deepLink.value = response.data.bot_url
  } catch { error.value = "Telegram bilan bog‘lanib bo‘lmadi. Qayta urinib ko‘ring." }
  finally { loading.value = false }
}
const openTelegram = () => {
  step.value = "code"
  error.value = ""
  void checkStatus()
  clearInterval(pollTimer)
  pollTimer = setInterval(() => { void checkStatus() }, 3000)
}
const verify = async () => {
  if (verifying.value || status.value !== "ready" || !/^[0-9]{5}$/.test(code.value)) return
  verifying.value = true; error.value = ""
  try {
    const response = await api.verifyTelegramCode({ code: code.value, session_id: session.value }, locale.value)
    setUser(response.data.user)
    stopTimers()
    emit("authenticated"); emit("update:modelValue", false)
  } catch {
    error.value = "Kod noto‘g‘ri yoki eskirgan."
    void checkStatus()
  } finally { verifying.value = false }
}
const onReturn = () => {
  if (document.visibilityState === "visible") {
    if (status.value === "ready") tick()
    void checkStatus()
  }
}
watch(() => props.modelValue, visible => {
  if (visible) void prepare()
  else { preparation++; stopTimers(); code.value = ""; session.value = ""; deepLink.value = "" }
}, { immediate: true })
onMounted(() => {
  document.addEventListener("visibilitychange", onReturn)
  window.addEventListener("focus", onReturn)
})
onBeforeUnmount(() => {
  stopTimers()
  document.removeEventListener("visibilitychange", onReturn)
  window.removeEventListener("focus", onReturn)
})
</script>
<template>
  <Teleport to="body">
    <div v-if="modelValue" id="telegram-code-dialog" class="tg-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="telegram-code-title" tabindex="-1" @click.self="close">
      <div class="tg-modal-card">
        <button type="button" class="tg-modal-close" aria-label="Yopish" :disabled="verifying" @click="close">✕</button>
        <div class="tg-modal-header"><h2 id="telegram-code-title" class="tg-modal-title">{{ title || t("auth.login_tab") || 'Kirish' }}</h2></div>
        <p v-if="error" class="form-message" role="alert">{{ error }}</p>
        <template v-if="step === 'telegram'">
          <a v-if="deepLink" :href="deepLink" target="_blank" rel="noopener noreferrer" class="primary-button tg-submit-btn" @click="openTelegram">
            <svg class="telegram-logo" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21.5 3.5 18.1 20c-.25 1.17-.94 1.45-1.9.9l-5.18-3.82-2.5 2.4c-.28.28-.52.52-1.06.52l.37-5.27L17.4 5.95c.42-.37-.09-.58-.65-.21L4.92 13.18l-5.1-1.6c-1.1-.34-1.12-1.1.23-1.63L20 2.27c.92-.34 1.72.21 1.5 1.23Z" transform="translate(1 0) scale(.95)" /></svg>
            Telegram orqali kirish
          </a>
          <button v-else type="button" class="primary-button tg-submit-btn" :disabled="loading" @click="prepare">{{ loading ? 'Yuklanmoqda…' : 'Qayta urinish' }}</button>
        </template>
        <form v-else class="telegram-code-form" @submit.prevent="verify">
          <input id="telegram-login-code" v-model="code" aria-label="Kirish kodi" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{5}" minlength="5" maxlength="5" placeholder="00000" required :disabled="verifying || status !== 'ready'" @input="code = code.replace(/[^0-9]/g, '').slice(0, 5)">
          <p class="code-countdown" :class="{ expired: status === 'expired' }" role="timer">{{ status === 'waiting' ? 'Kod kutilmoqda…' : status === 'expired' ? 'Kod muddati tugadi' : `${remaining} sekund` }}</p>
          <button type="submit" class="primary-button" :disabled="verifying || status !== 'ready' || code.length !== 5">{{ verifying ? 'Tekshirilmoqda…' : 'Kirish' }}</button>
          <button v-if="status === 'expired'" type="button" class="secondary-button" :disabled="verifying || loading" @click="prepare">Kodni olish</button>
          <a v-else-if="status === 'waiting'" :href="deepLink" target="_blank" rel="noopener noreferrer" class="secondary-button tg-submit-btn">Telegramni ochish</a>
        </form>
      </div>
    </div>
  </Teleport>
</template>
<style scoped>
.telegram-code-form { display: grid; gap: 12px; margin: 20px 0; }
.telegram-code-form input { width: 100%; min-height: 52px; text-align: center; font-size: 24px; letter-spacing: 8px; color: var(--text); background: var(--control); border: 1px solid var(--panel-border); border-radius: 10px; }
.code-countdown { margin: 0; text-align: center; color: var(--muted); font-variant-numeric: tabular-nums; }
.code-countdown.expired { color: var(--danger, #dc2626); }
.telegram-logo { width: 22px; height: 22px; flex-shrink: 0; }
.telegram-code-form .secondary-button { width: 100%; justify-content: center; }
.tg-submit-btn { text-decoration: none; justify-content: center; }
.tg-modal-card { max-height: calc(100dvh - 32px); overflow-y: auto; }

.tg-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(12px);
  animation: modalFadeIn 0.2s ease-out;
}

.tg-modal-card {
  position: relative;
  width: min(100%, 420px);
  padding: 32px 28px;
  border-radius: 24px;
  background: var(--surface);
  border: 1px solid var(--panel-border);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  color: var(--text);
  animation: modalSlideUp 0.25s ease-out;
}

.tg-modal-close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--control);
  color: var(--muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tg-modal-close:hover {
  color: var(--text);
  border-color: var(--accent);
}

.tg-modal-header {
  text-align: center;
  margin-bottom: 24px;
}

.tg-modal-title {
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.tg-modal-description {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.4;
}

.tg-modal-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 30px 10px;
  text-align: center;
  color: var(--muted);
}

.auth-spinner {
  width: 34px;
  height: 34px;
  border: 3px solid color-mix(in srgb, var(--accent) 20%, transparent);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes modalFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes modalSlideUp {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

</style>
