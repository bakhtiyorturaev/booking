<script setup lang="ts">
import { useAuth } from "~/composables/useAuth"
import { useTelegramWebApp } from "~/composables/useTelegramWebApp"
import { useAuthApi } from "~/api/auth"
import { useTranslations } from "~/composables/useTranslations"

const props = defineProps<{
  modelValue: boolean
  title?: string
  description?: string
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void
  (e: "authenticated" | "close"): void
}>()

const { isTMA, initTMA, haptic } = useTelegramWebApp()
const { load, user, setUser } = useAuth()
const { locale, load: loadTranslations, t } = useTranslations()
const authApi = useAuthApi()

await loadTranslations()
if (["auth.telegram_quick_login", "auth.telegram_login_subtitle", "auth.telegram_qr_instruction", "auth.open_in_telegram", "auth.waiting_bot_confirmation", "auth.connecting_telegram"].some(code => t(code) === code)) {
  await loadTranslations(locale.value, true).catch(() => undefined)
}

const deepLink = ref("")
const token = ref("")
const isLoading = ref(false)
const isPolling = ref(false)
const isChecking = ref(false)
const errorMessage = ref("")
let pollInterval: ReturnType<typeof setInterval> | null = null

const qrCodeUrl = computed(() => {
  if (!deepLink.value) return ""
  return `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(deepLink.value)}&margin=8`
})

const formattedErrorMessage = computed(() => {
  if (!errorMessage.value) return ""
  if (/^[a-z0-9_]+(?:\.[a-z0-9_]+)+$/.test(errorMessage.value)) {
    return t(errorMessage.value)
  }
  return errorMessage.value
})

const startWebLogin = async () => {
  isLoading.value = true
  errorMessage.value = ""
  try {
    const response = await authApi.initTelegramWebLogin(locale.value)
    token.value = response.data.token
    deepLink.value = response.data.deep_link
    if (!import.meta.server) {
      try {
        sessionStorage.setItem("tg_web_login_token", response.data.token)
      } catch {
        // Ignored
      }
    }
    startPolling()
  } catch (error: any) {
    const code = error?.data?.code || error?.code || error?.message || "common.backend_unavailable"
    errorMessage.value = code
  } finally {
    isLoading.value = false
  }
}

const checkNow = async () => {
  if (!token.value || isChecking.value) return
  isChecking.value = true

  try {
    const response = await authApi.checkTelegramWebLogin(token.value, locale.value)
    if (response.data?.status === "SUCCESS") {
      stopPolling()
      if (!import.meta.server) {
        try {
          sessionStorage.removeItem("tg_web_login_token")
        } catch {
          // Ignored
        }
      }
      if (response.data.user) {
        setUser(response.data.user)
      }
      await load(true).catch(() => undefined)
      haptic("success")
      useToast().success(t("auth.login_success") || "Tizimga muvaffaqiyatli kirdingiz!")
      emit("authenticated")
      emit("update:modelValue", false)
    }
  } catch (error: any) {
    if (error?.data?.code === "auth.session_expired") {
      if (!import.meta.server) {
        try {
          sessionStorage.removeItem("tg_web_login_token")
        } catch {
          // Ignored
        }
      }
    }
  } finally {
    isChecking.value = false
  }
}

const onFocus = () => {
  if (isPolling.value) void checkNow()
}

const onVisibilityChange = () => {
  if (document.visibilityState === "visible" && isPolling.value) {
    void checkNow()
  }
}

const startPolling = () => {
  stopPolling()
  if (!token.value) return
  isPolling.value = true

  pollInterval = setInterval(() => {
    void checkNow()
  }, 1200)

  if (!import.meta.server) {
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onVisibilityChange)
  }
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
  if (!import.meta.server) {
    window.removeEventListener("focus", onFocus)
    document.removeEventListener("visibilitychange", onVisibilityChange)
  }
  isPolling.value = false
}

const handleTmaLogin = async () => {
  isLoading.value = true
  try {
    await initTMA()
    if (user.value) {
      emit("authenticated")
      emit("update:modelValue", false)
    }
  } finally {
    isLoading.value = false
  }
}

const openTelegramLink = () => {
  if (deepLink.value) {
    window.open(deepLink.value, "_blank")
  }
}

const close = () => {
  stopPolling()
  emit("update:modelValue", false)
  emit("close")
}

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      if (isTMA.value) {
        void handleTmaLogin()
      } else {
        void startWebLogin()
      }
    } else {
      stopPolling()
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="tg-modal-backdrop"
      @click.self="close"
    >
      <div class="tg-modal-card">
        <!-- Close Button -->
        <button
          type="button"
          class="tg-modal-close"
          aria-label="Close"
          @click="close"
        >
          ✕
        </button>

        <!-- Header -->
        <div class="tg-modal-header">
          <div class="tg-icon-bubble">
            <svg class="tg-svg-mark" viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
            </svg>
          </div>
          <h2 class="tg-modal-title">
            {{ title || t("auth.telegram_quick_login") }}
          </h2>
          <p class="tg-modal-description">
            {{ description || t("auth.telegram_login_subtitle") }}
          </p>
        </div>

        <!-- Body State Handling -->
        <div v-if="isLoading" class="tg-modal-status">
          <span class="auth-spinner" />
          <p>{{ t("auth.connecting_telegram") }}</p>
        </div>

        <div v-else-if="errorMessage" class="tg-modal-status">
          <p class="form-message" role="alert">{{ formattedErrorMessage }}</p>
          <button type="button" class="secondary-button" @click="startWebLogin">
            {{ t("common.retry") }}
          </button>
        </div>

        <div v-else class="tg-modal-content">
          <!-- QR Code for Desktop -->
          <div class="tg-qr-box">
            <div class="tg-qr-inner">
              <img
                v-if="qrCodeUrl"
                :src="qrCodeUrl"
                alt="Telegram Login QR"
                class="tg-qr-img"
              >
            </div>
            <p class="tg-qr-text">
              {{ t("auth.telegram_qr_instruction") }}
            </p>
          </div>

          <!-- Direct Deep Link Button -->
          <button
            type="button"
            class="primary-button tg-submit-btn"
            @click="openTelegramLink"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
            </svg>
            <span>{{ t("auth.open_in_telegram") }}</span>
          </button>

          <!-- Polling State -->
          <div v-if="isPolling" class="tg-polling-indicator">
            <span class="tg-pulse-circle" />
            <span>{{ t("auth.waiting_bot_confirmation") }}</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
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
