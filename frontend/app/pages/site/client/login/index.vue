<script setup lang="ts">
import ChangePasswordModal from "~/components/auth/ChangePasswordModal.vue"
import { useAuth } from "~/composables/useAuth"
import { useTranslations } from "~/composables/useTranslations"

definePageMeta({ middleware: "guest" })

const route = useRoute()
const { t } = useTranslations()
const { loginWithPassword } = useAuth("client")

useHead({
  title: "Klub egalari va hamkorlar uchun kirish — RezervUZ",
})

const loginInput = ref("")
const passwordInput = ref("")
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref("")
const showPasswordExpiredModal = ref(false)

const formattedErrorMessage = computed(() => {
  if (!errorMessage.value) return ""
  if (errorMessage.value === "auth.invalid_credentials") {
    return "Login yoki parol noto‘g‘ri kiritildi"
  }
  if (errorMessage.value === "auth.client_access_denied") {
    return "Bu bo‘lim faqat klub egalari va xizmat ko‘rsatuvchi hamkorlar uchun mo‘ljallangan."
  }
  if (errorMessage.value === "auth.user_inactive") {
    return "Foydalanuvchi hisobi faol emas yoki bloklangan."
  }
  return t(errorMessage.value) || errorMessage.value
})

const onPasswordLogin = async () => {
  errorMessage.value = ""
  if (!loginInput.value.trim() || !passwordInput.value) {
    errorMessage.value = "Login va parolni kiriting"
    return
  }

  isLoading.value = true
  try {
    const result = await loginWithPassword({
      login: loginInput.value.trim(),
      password: passwordInput.value,
      login_type: "client",
    })

    if (result.password_expired || result.user?.password_expired) {
      showPasswordExpiredModal.value = true
    } else {
      await redirectAfterLogin()
    }
  } catch (error: any) {
    errorMessage.value = error?.code || error?.data?.code || error?.message || "auth.invalid_credentials"
  } finally {
    isLoading.value = false
  }
}

const onPasswordChangeSuccess = async () => {
  showPasswordExpiredModal.value = false
  await redirectAfterLogin()
}

const redirectAfterLogin = async () => {
  const requested = route.query.redirect
  const base = "/site/client/panel"
  const target = typeof requested === "string" && (requested === base || requested.startsWith(`${base}/`)) && !requested.includes("\\") ? requested : base
  await navigateTo(target)
}
</script>

<template>
  <div class="client-login-page">
    <div class="client-login-card">
      <!-- Header -->
      <div class="card-header">
        <div class="badge-tag">
          <i class="fa-solid fa-briefcase" />
          <span>Hamkorlar portali</span>
        </div>
        <h1 class="card-title">Klub egalari va servislar kabineti</h1>
        <p class="card-subtitle">
          Klub, filial va xizmatlarni boshqarish uchun tizimga kiring
        </p>
      </div>

      <!-- Xato xabari -->
      <div v-if="errorMessage" class="error-alert" role="alert">
        <i class="fa-solid fa-triangle-exclamation" />
        <span>{{ formattedErrorMessage }}</span>
      </div>

      <!-- Login Form -->
      <form class="login-form" @submit.prevent="onPasswordLogin">
        <div class="form-group">
          <label for="client-login" class="form-label">
            <i class="fa-solid fa-user" />
            <span>Login yoki telefon raqam</span>
          </label>
          <input
            id="client-login"
            v-model="loginInput"
            type="text"
            class="form-input"
            placeholder="masalan: owner_user yoki +998901234567"
            autocomplete="username"
            :disabled="isLoading"
          />
        </div>

        <div class="form-group">
          <label for="client-password" class="form-label">
            <i class="fa-solid fa-lock" />
            <span>Parol</span>
          </label>
          <div class="password-input-wrap">
            <input
              id="client-password"
              v-model="passwordInput"
              :type="showPassword ? 'text' : 'password'"
              class="form-input"
              placeholder="Parolni kiriting"
              autocomplete="current-password"
              :disabled="isLoading"
            />
            <button
              type="button"
              class="toggle-password-btn"
              :title="showPassword ? 'Yashirish' : 'Ko‘rsatish'"
              @click="showPassword = !showPassword"
            >
              <i :class="showPassword ? 'fa-regular fa-eye-slash' : 'fa-regular fa-eye'" />
            </button>
          </div>
        </div>

        <button
          type="submit"
          class="submit-btn"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="spinner" />
          <i v-else class="fa-solid fa-arrow-right-to-bracket" />
          <span>{{ isLoading ? "Kirilmoqda..." : "Kabinetga kirish" }}</span>
        </button>
      </form>
    </div>

    <!-- Parol eskirganida ochiladigan modal -->
    <ChangePasswordModal
      v-model="showPasswordExpiredModal"
      :force="true"
      @close="showPasswordExpiredModal = false"
      @success="onPasswordChangeSuccess"
    />
  </div>
</template>

<style scoped>
.client-login-page {
  min-height: calc(100vh - 120px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.client-login-card {
  width: 100%;
  max-width: 440px;
  background: var(--surface-primary, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 1.25rem;
  padding: 2.25rem 2rem;
  box-shadow: 0 4px 24px -2px rgba(0, 0, 0, 0.08);
}

.card-header {
  text-align: center;
  margin-bottom: 1.75rem;
}

.badge-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #0369a1;
  background: #e0f2fe;
  margin-bottom: 0.85rem;
}

.card-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary, #111827);
  margin: 0 0 0.4rem;
  line-height: 1.25;
}

.card-subtitle {
  font-size: 0.875rem;
  color: var(--text-muted, #6b7280);
  margin: 0;
  line-height: 1.4;
}

.error-alert {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  border-radius: 0.65rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 0.84rem;
  line-height: 1.4;
  margin-bottom: 1.25rem;
}

.error-alert i {
  margin-top: 0.15rem;
  flex-shrink: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.825rem;
  font-weight: 500;
  color: var(--text-secondary, #374151);
}

.form-label i {
  color: var(--text-muted, #9ca3af);
  font-size: 0.8rem;
}

.form-input {
  width: 100%;
  padding: 0.7rem 0.9rem;
  border: 1px solid var(--border-color, #d1d5db);
  border-radius: 0.65rem;
  font-size: 0.9rem;
  background: var(--surface-secondary, #f9fafb);
  color: var(--text-primary, #111827);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #0284c7;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15);
}

.password-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.password-input-wrap .form-input {
  padding-right: 2.75rem;
}

.toggle-password-btn {
  position: absolute;
  right: 0.75rem;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted, #9ca3af);
  padding: 0.25rem;
  font-size: 0.95rem;
  line-height: 1;
}

.toggle-password-btn:hover {
  color: var(--text-primary, #111827);
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem 1rem;
  border: none;
  border-radius: 0.65rem;
  background: #0284c7;
  color: #ffffff;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  margin-top: 0.4rem;
  transition: background-color 0.15s, opacity 0.15s;
}

.submit-btn:hover:not(:disabled) {
  background: #0369a1;
}

.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.spinner {
  width: 1.1rem;
  height: 1.1rem;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
