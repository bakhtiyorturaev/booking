<script setup lang="ts">
import { useAuth } from "~/composables/useAuth"
import { useTelegramWebApp } from "~/composables/useTelegramWebApp"
import { useAuthApi } from "~/api/auth"
import { useTranslations } from "~/composables/useTranslations"

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void
  (e: "saved", phone: string): void
  (e: "close"): void
}>()

const { isTMA, haptic } = useTelegramWebApp()
const { load, user, setUser } = useAuth()
const { locale, load: loadTranslations, t } = useTranslations()
const authApi = useAuthApi()

await loadTranslations()
if (["auth.phone_number", "auth.phone_required_for_booking", "auth.share_telegram_phone", "auth.enter_phone", "common.save"].some(code => t(code) === code)) {
  await loadTranslations(locale.value, true).catch(() => undefined)
}

const phoneInput = ref("")
const isLoading = ref(false)
const errorMessage = ref("")

const formattedErrorMessage = computed(() => {
  if (!errorMessage.value) return ""
  if (/^[a-z0-9_]+(?:\.[a-z0-9_]+)+$/.test(errorMessage.value)) {
    return t(errorMessage.value)
  }
  return errorMessage.value
})

const handleTmaRequestContact = () => {
  if (import.meta.server) return
  const tg = window.Telegram?.WebApp
  if (!tg) return

  isLoading.value = true
  errorMessage.value = ""

  if ((tg as any).requestContact) {
    (tg as any).requestContact(async (ok: boolean, response: any) => {
      if (ok && response?.responseUnsafe?.contact?.phone_number) {
        const phone = response.responseUnsafe.contact.phone_number
        await submitPhone(phone)
      } else {
        isLoading.value = false
      }
    })
  } else {
    isLoading.value = false
  }
}

const submitPhone = async (phoneToSubmit?: string) => {
  let raw = (phoneToSubmit || phoneInput.value).replace(/\s+/g, "").replace(/-/g, "").replace(/\(/g, "").replace(/\)/g, "").trim()
  if (!raw) {
    errorMessage.value = t("auth.phone_number")
    return
  }

  let phone = raw
  if (!phone.startsWith("+")) {
    if (phone.startsWith("998")) {
      phone = `+${phone}`
    } else if (phone.length === 9) {
      phone = `+998${phone}`
    } else {
      phone = `+${phone}`
    }
  }

  isLoading.value = true
  errorMessage.value = ""

  try {
    if (!user.value && !import.meta.server && window.Telegram?.WebApp?.initData) {
      try {
        const loginRes = await authApi.telegramMiniAppLogin(window.Telegram.WebApp.initData, locale.value)
        setUser(loginRes.data.user)
      } catch {
        // Ignored
      }
    }

    const response = await authApi.saveTelegramContact({ phone }, locale.value)
    await load(true)
    haptic("success")
    useToast().success(t("auth.phone_saved_success") || "Telefon raqamingiz saqlandi!")
    emit("saved", response.data.phone)
    emit("update:modelValue", false)
  } catch (error: any) {
    const code = error?.data?.code || error?.code || error?.message || "common.backend_unavailable"
    errorMessage.value = code
    haptic("error")
    useToast().error(formattedErrorMessage.value || code)
  } finally {
    isLoading.value = false
  }
}

const close = () => {
  emit("update:modelValue", false)
  emit("close")
}
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
          <div class="tg-icon-bubble tg-contact-bubble">
            <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
            </svg>
          </div>
          <h2 class="tg-modal-title">
            {{ t("auth.enter_phone") }}
          </h2>
          <p class="tg-modal-description">
            {{ t("auth.phone_required_for_booking") }}
          </p>
        </div>

        <!-- Error message -->
        <p v-if="errorMessage" class="form-message" role="alert">
          {{ formattedErrorMessage }}
        </p>

        <!-- Content -->
        <div class="tg-modal-content">
          <!-- TMA Native Contact Button -->
          <button
            v-if="isTMA"
            type="button"
            class="primary-button tg-submit-btn"
            :disabled="isLoading"
            @click="handleTmaRequestContact"
          >
            <span>{{ t("auth.share_telegram_phone") }}</span>
          </button>

          <div v-if="isTMA" class="tg-divider">
            <span />
          </div>

          <!-- Phone input for manual entry -->
          <div class="field-group">
            <label>{{ t("auth.phone_number") }}</label>
            <div class="phone-control">
              <span class="phone-prefix">+998</span>
              <input
                v-model="phoneInput"
                type="tel"
                placeholder="90 123 45 67"
                @keyup.enter="() => submitPhone()"
              >
            </div>
          </div>

          <button
            type="button"
            class="primary-button tg-submit-btn"
            :disabled="isLoading || !phoneInput.trim()"
            @click="() => submitPhone()"
          >
            <span>{{ isLoading ? t("common.loading") : t("common.save") }}</span>
          </button>
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
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #ffffff;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);
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

.tg-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tg-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 4px 0;
}

.tg-divider span {
  width: 100%;
  height: 1px;
  background: var(--border);
}

.tg-submit-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
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
