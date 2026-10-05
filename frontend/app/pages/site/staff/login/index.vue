<script setup lang="ts">
import ChangePasswordModal from "~/components/auth/ChangePasswordModal.vue"
import { useAuth } from "~/composables/useAuth"
import { useTranslations } from "~/composables/useTranslations"

definePageMeta({ middleware: "guest" })

const route = useRoute()
const { t } = useTranslations()
const { loginWithPassword } = useAuth("staff")

useHead({
  title: "Xodimlar va operatorlar uchun kirish — RezervUZ Cabinet",
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
  if (errorMessage.value === "auth.staff_access_denied") {
    return "Bu bo‘lim faqat xodimlar va operatorlar uchun. Mijozlar Telegram orqali kirishi mumkin."
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
      login_type: "staff",
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
  const base = "/site/staff/panel"
  const target = typeof requested === "string" && (requested === base || requested.startsWith(`${base}/`)) && !requested.includes("\\") ? requested : base
  await navigateTo(target)
}
</script>

<template>
  <div class="staff-login-page">
    <div class="staff-login-card">
      <!-- Header -->
      <div class="card-header">
        <div class="badge-tag">
          <i class="fa-solid fa-shield-halved" />
          <span>Xodimlar portali</span>
        </div>
        <h1 class="card-title">RezervUZ Cabinet</h1>
        <p class="card-subtitle">
          Klub egalari, filial boshqaruvchilari va operatorlar uchun boshqaruv tizimi
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
          <label for="staff-login" class="form-label">
            <i class="fa-solid fa-user" />
            <span>Login yoki telefon raqam</span>
          </label>
          <input
            id="staff-login"
            v-model="loginInput"
            type="text"
            required
            autocomplete="username"
            placeholder="masalan: admin_club yoki +998901234567"
            class="form-input"
            :disabled="isLoading"
          >
        </div>

        <div class="form-group">
          <label for="staff-password" class="form-label">
            <i class="fa-solid fa-lock" />
            <span>Parol</span>
          </label>
          <div class="password-wrapper">
            <input
              id="staff-password"
              v-model="passwordInput"
              :type="showPassword ? 'text' : 'password'"
              required
              autocomplete="current-password"
              placeholder="Parolni kiriting"
              class="form-input"
              :disabled="isLoading"
            >
            <button
              type="button"
              class="password-toggle"
              aria-label="Toggle password visibility"
              @click="showPassword = !showPassword"
            >
              <i :class="showPassword ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'" />
            </button>
          </div>
        </div>

        <button
          type="submit"
          class="submit-button"
          :disabled="isLoading || !loginInput || !passwordInput"
        >
          <span v-if="isLoading" class="btn-spinner" />
          <span>{{ isLoading ? "Kirilmoqda..." : "Kabinetga kirish" }}</span>
          <i v-if="!isLoading" class="fa-solid fa-arrow-right" />
        </button>
      </form>

      <!-- Bottom link to customer login -->
      <div class="card-footer">
        <NuxtLink to="/login" class="customer-link">
          <i class="fa-solid fa-arrow-left" />
          <span>Mijozlar uchun kirish (Telegram orqali)</span>
        </NuxtLink>
      </div>
    </div>

    <!-- Majburiy parolni yangilash modali (1 oydan oshgan bo'lsa) -->
    <ChangePasswordModal
      v-model="showPasswordExpiredModal"
      :force="true"
      title="Parolni yangilash talab etiladi"
      description="Xavfsizlik qoidalariga ko‘ra xodimlar paroli har 1 oyda yangilanishi lozim. Yangi parol o‘rnating."
      @success="onPasswordChangeSuccess"
    />
  </div>
</template>

<style scoped>
.staff-login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  background: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 100%);
  color: #f8fafc;
}

.staff-login-card {
  width: min(100%, 440px);
  padding: 40px 32px;
  border-radius: 24px;
  background: rgba(30, 41, 59, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(16px);
}

.card-header {
  text-align: center;
  margin-bottom: 28px;
}

.badge-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 9999px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 14px;
}

.card-title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #ffffff;
}

.card-subtitle {
  margin: 0;
  font-size: 13.5px;
  color: #94a3b8;
  line-height: 1.5;
}

.error-alert {
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #fca5a5;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
}

.form-label i {
  color: #38bdf8;
  font-size: 12px;
}

.form-input {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(15, 23, 42, 0.6);
  color: #ffffff;
  font-size: 14.5px;
  outline: none;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #38bdf8;
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.25);
  background: rgba(15, 23, 42, 0.85);
}

.password-wrapper {
  position: relative;
  width: 100%;
}

.password-wrapper .form-input {
  padding-right: 48px;
}

.password-toggle {
  position: absolute;
  top: 0;
  right: 0;
  height: 48px;
  width: 48px;
  display: grid;
  place-items: center;
  border: none;
  background: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 15px;
  transition: color 0.15s;
}

.password-toggle:hover {
  color: #ffffff;
}

.submit-button {
  width: 100%;
  height: 50px;
  margin-top: 6px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  color: #ffffff;
  font-size: 15px;
  font-weight: 650;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 18px rgba(2, 132, 199, 0.35);
}

.submit-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 22px rgba(2, 132, 199, 0.45);
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.card-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.customer-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 13px;
  text-decoration: none;
  transition: color 0.15s;
}

.customer-link:hover {
  color: #38bdf8;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
