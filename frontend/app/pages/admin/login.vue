<script setup lang="ts">
import { useAuthApi } from "~/api/auth"
import { useAuth } from "~/composables/useAuth"
import { ApiRequestError } from "~/types/api"

definePageMeta({
  layout: false,
})

useHead({
  title: "Xodimlar kirishi",
})

const authApi = useAuthApi()
const { setUser, load } = useAuth()
const route = useRoute()

const username = ref("")
const password = ref("")
const isLoading = ref(false)
const errorMessage = ref("")

const redirectTarget = computed(() => {
  const raw = route.query.redirect
  const value = Array.isArray(raw) ? raw[0] : raw
  return value && value.startsWith("/") ? value : "/admin"
})

// Agar allaqachon xodim sifatida kirilgan bo'lsa — to'g'ridan-to'g'ri panelga.
onMounted(async () => {
  const user = await load()
  const role = user?.role
  if (role === "ADMIN" || role === "MODERATOR") {
    await navigateTo(redirectTarget.value)
  }
})

const handleSubmit = async () => {
  if (!username.value.trim() || !password.value) {
    errorMessage.value = "Login va parolni kiriting"
    return
  }
  isLoading.value = true
  errorMessage.value = ""
  try {
    const response = await authApi.staffLogin(username.value.trim(), password.value, "uz")
    setUser(response.data.user)
    await navigateTo(redirectTarget.value)
  } catch (error) {
    if (error instanceof ApiRequestError && error.statusCode !== 401) {
      errorMessage.value = error.message || "Kirishda xatolik yuz berdi"
    } else {
      errorMessage.value = "Login yoki parol noto'g'ri, yoki sizda ruxsat yo'q"
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="staff-login">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-logo-badge">⚡</div>
        <div class="brand-text">
          <span class="brand-title">Rezerv<span style="color: #6366f1;">UZ</span></span>
          <span class="brand-subtitle">Xodimlar Kabineti</span>
        </div>
      </div>

      <h1 class="login-title">Tizimga kirish</h1>
      <p class="login-subtitle">Admin yoki moderator hisobingiz bilan kiring</p>

      <form class="login-form" @submit.prevent="handleSubmit">
        <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

        <div class="form-group">
          <label for="staff-username">Login</label>
          <input
            id="staff-username"
            v-model="username"
            type="text"
            autocomplete="username"
            placeholder="Foydalanuvchi nomi"
            :disabled="isLoading"
          >
        </div>

        <div class="form-group">
          <label for="staff-password">Parol</label>
          <input
            id="staff-password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="••••••••"
            :disabled="isLoading"
          >
        </div>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          {{ isLoading ? "Kirilmoqda..." : "Kirish" }}
        </button>
      </form>

      <p class="login-hint">
        Bu sahifa faqat xodimlar uchun. Oddiy foydalanuvchilar
        <NuxtLink to="/login">Telegram orqali kirishi</NuxtLink> mumkin.
      </p>
    </div>
  </div>
</template>

<style scoped>
.staff-login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  background: var(--bg, #0f172a);
  color: var(--text, #e2e8f0);
}

.login-card {
  width: min(100%, 420px);
  padding: 32px 28px;
  background: var(--surface, #1e293b);
  border: 1px solid var(--panel-border, #334155);
  border-radius: 20px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.35);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.brand-logo-badge {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-size: 22px;
  background: linear-gradient(135deg, #6366f1 0%, #0088cc 100%);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.brand-title {
  font-size: 18px;
  font-weight: 800;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--muted, #94a3b8);
}

.login-title {
  margin: 8px 0 2px;
  font-size: 22px;
  font-weight: 800;
}

.login-subtitle {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--muted, #94a3b8);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted, #94a3b8);
}

.form-group input {
  padding: 11px 13px;
  border-radius: 10px;
  border: 1px solid var(--border, #334155);
  background: var(--control, #0f172a);
  color: var(--text, #e2e8f0);
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent, #6366f1);
}

.submit-btn {
  margin-top: 4px;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-error {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  font-size: 13px;
}

.login-hint {
  margin: 14px 0 0;
  font-size: 12px;
  color: var(--muted, #94a3b8);
  text-align: center;
}

.login-hint a {
  color: var(--accent, #6366f1);
  font-weight: 600;
}
</style>
