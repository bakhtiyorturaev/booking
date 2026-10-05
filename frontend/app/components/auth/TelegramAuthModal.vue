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
const loading = ref(false)
const verifying = ref(false)
const error = ref("")
const close = () => { if (!verifying.value) { emit("update:modelValue", false); emit("close") } }
const opened = computed(() => props.modelValue)
useDialogFocus(opened, "#telegram-code-dialog", close)
const start = async () => {
  if (loading.value) return
  loading.value = true; error.value = ""; code.value = ""
  try {
    if (isTMA.value) {
      await initTMA()
      const { user } = useAuth("customer")
      if (user.value) { emit("authenticated"); emit("update:modelValue", false); return }
      throw new Error("Telegram orqali kirib bo‘lmadi. Qayta urinib ko‘ring.")
    }
    const response = await api.initTelegramCodeLogin(locale.value)
    session.value = response.data.session_id
    deepLink.value = response.data.bot_url
  } catch { error.value = "Telegram bilan bog‘lanib bo‘lmadi. Qayta urinib ko‘ring." }
  finally { loading.value = false }
}
const verify = async () => {
  if (verifying.value || !/^[0-9]{5}$/.test(code.value)) return
  verifying.value = true; error.value = ""
  try {
    const response = await api.verifyTelegramCode({ code: code.value, session_id: session.value }, locale.value)
    setUser(response.data.user)
    emit("authenticated"); emit("update:modelValue", false)
  } catch { error.value = "Kod noto‘g‘ri yoki eskirgan. Telegram’dan yangi kod oling." }
  finally { verifying.value = false }
}
watch(() => props.modelValue, visible => { if (visible) void start(); else { code.value = ""; session.value = "" } }, { immediate: true })
</script>
<template>
  <Teleport to="body">
    <div v-if="modelValue" id="telegram-code-dialog" class="tg-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="telegram-code-title" tabindex="-1" @click.self="close">
      <div class="tg-modal-card">
        <button type="button" class="tg-modal-close" aria-label="Yopish" :disabled="verifying" @click="close">✕</button>
        <div class="tg-modal-header"><h2 id="telegram-code-title" class="tg-modal-title">{{ title || t("auth.login_tab") || 'Kirish' }}</h2><p class="tg-modal-description">{{ description || 'Botda Start tugmasini bosing. Keyin 5 xonali kodni shu yerga kiriting.' }}</p></div>
        <p v-if="error" class="form-message" role="alert">{{ error }}</p>
        <div v-if="loading" class="tg-modal-status"><span class="auth-spinner" /><p>Yuklanmoqda…</p></div>
        <template v-else>
          <a v-if="deepLink" :href="deepLink" target="_blank" rel="noopener noreferrer" class="primary-button tg-submit-btn">Telegram orqali kirish</a>
          <form v-if="session" class="telegram-code-form" @submit.prevent="verify">
            <label for="telegram-login-code">Telegram kodi</label>
            <input id="telegram-login-code" v-model="code" type="text" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{5}" minlength="5" maxlength="5" placeholder="12345" required :disabled="verifying">
            <small>Kod berilganidan boshlab 1 daqiqa amal qiladi.</small>
            <button type="submit" class="primary-button" :disabled="verifying || code.length !== 5">{{ verifying ? 'Tekshirilmoqda…' : 'Kirish' }}</button>
          </form>
          <button type="button" class="secondary-button" :disabled="verifying" @click="start">Yangi kod olish</button>
        </template>
      </div>
    </div>
  </Teleport>
</template>
<style scoped>
.telegram-code-form { display: grid; gap: 12px; margin: 20px 0; }
.telegram-code-form input { width: 100%; min-height: 52px; text-align: center; font-size: 24px; letter-spacing: 8px; color: var(--text); background: var(--control); border: 1px solid var(--panel-border); border-radius: 10px; }
.telegram-code-form small { color: var(--muted); line-height: 1.5; }
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

.tg-icon-bubble {
  width: 56px;
  height: 56px;
  margin: 0 auto 14px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--accent) 0%, #0088cc 100%);
  color: #ffffff;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--accent) 30%, transparent);
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

.tg-modal-content {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.tg-qr-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--control) 60%, transparent);
  border: 1px solid var(--panel-border);
}

.tg-qr-inner {
  padding: 8px;
  background: #ffffff;
  border-radius: 12px;
  display: inline-flex;
}

.tg-qr-img {
  width: 160px;
  height: 160px;
  display: block;
}

.tg-qr-text {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}

.tg-submit-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.tg-polling-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--accent);
}

.tg-pulse-circle {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 1.5s infinite;
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

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.8); }
}

@media (max-width: 500px) {
  .tg-qr-box {
    display: none;
  }
}
</style>
