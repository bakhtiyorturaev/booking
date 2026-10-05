<script setup lang="ts">
import PortalLoginForm from "~/components/auth/PortalLoginForm.vue"
import ChangePasswordModal from "~/components/auth/ChangePasswordModal.vue"
import { useAuth } from "~/composables/useAuth"
import { useTranslations } from "~/composables/useTranslations"

definePageMeta({ middleware: "guest" })

const route = useRoute()
const { t } = useTranslations()
const { loginWithPassword } = useAuth("client")

useHead({ title: "Hamkorlar portali — RezervUZ" })

const loginInput = ref("")
const passwordInput = ref("")
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
  <div>
    <PortalLoginForm
      v-model:login="loginInput"
      v-model:password="passwordInput"
      portal="Hamkorlar portali"
      id-prefix="client"
      :loading="isLoading"
      :error="formattedErrorMessage"
      @submit="onPasswordLogin"
    />
    <ChangePasswordModal
      v-model="showPasswordExpiredModal"
      :force="true"
      @success="onPasswordChangeSuccess"
    />
  </div>
</template>
