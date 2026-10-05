<script setup lang="ts">
defineProps<{
  portal: string
  idPrefix: string
  loading: boolean
  error?: string
}>()
const login = defineModel<string>("login", { required: true })
const password = defineModel<string>("password", { required: true })
const emit = defineEmits<{ (event: "submit"): void }>()
const showPassword = ref(false)
</script>

<template>
  <div class="portal-login-page">
    <section class="portal-login-card" :aria-labelledby="`${idPrefix}-title`">
      <h1 :id="`${idPrefix}-title`">{{ portal }}</h1>
      <p v-if="error" class="login-error" role="alert">{{ error }}</p>
      <form class="login-form" :aria-busy="loading" @submit.prevent="emit('submit')">
        <div class="login-field">
          <label :for="`${idPrefix}-login`">Login</label>
          <input :id="`${idPrefix}-login`" v-model="login" type="text" autocomplete="username" required :disabled="loading" autocapitalize="none" :spellcheck="false">
        </div>
        <div class="login-field">
          <label :for="`${idPrefix}-password`">Parol</label>
          <div class="password-field">
            <input :id="`${idPrefix}-password`" v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" required :disabled="loading">
            <button type="button" class="password-toggle" :aria-label="showPassword ? 'Parolni yashirish' : 'Parolni ko‘rsatish'" :aria-pressed="showPassword" :disabled="loading" @click="showPassword = !showPassword">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
                <circle cx="12" cy="12" r="3" />
                <path v-if="showPassword" d="m3 3 18 18" />
              </svg>
            </button>
          </div>
        </div>
        <button type="submit" class="primary-button login-submit" :disabled="loading || !login.trim() || !password">
          {{ loading ? 'Kirilmoqda…' : 'Kirish' }}
        </button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.portal-login-page {
  min-height: calc(100dvh - 160px);
  display: grid;
  place-items: center;
  padding: 32px 16px;
}
.portal-login-card {
  width: min(100%, 400px);
  padding: 32px 28px;
  border: 1px solid var(--panel-border);
  border-radius: 20px;
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12);
}
h1 {
  margin: 0 0 28px;
  text-align: center;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.login-form { display: grid; gap: 20px; }
.login-field { display: grid; gap: 8px; }
label { font-size: 14px; font-weight: 600; }
input {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  height: 48px;
  padding: 0 14px;
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  background: var(--control);
  color: var(--text);
  font-size: 16px;
  outline: none;
}
input:focus-visible { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent); }
.password-field { position: relative; }
.password-field input { padding-right: 48px; }
.password-toggle {
  position: absolute;
  top: 0;
  right: 0;
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}
.password-toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: -4px; }
.login-submit { width: 100%; margin-top: 4px; }
.login-error {
  margin: 0 0 20px;
  padding: 12px;
  border-radius: 10px;
  color: var(--danger, #dc2626);
  background: color-mix(in srgb, var(--danger, #dc2626) 10%, var(--surface));
  font-size: 13px;
  line-height: 1.5;
}
@media (max-width: 400px) {
  .portal-login-card { padding: 28px 20px; }
}
</style>
