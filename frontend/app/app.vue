<script setup lang="ts">
import { useTelegramWebApp } from "~/composables/useTelegramWebApp"
import { useAuth } from "~/composables/useAuth"
import { useTranslations } from "~/composables/useTranslations"
import { useAuthApi } from "~/api/auth"

const { initTMA } = useTelegramWebApp()
const { user, setUser, load } = useAuth()
const { locale } = useTranslations()
const authApi = useAuthApi()

const checkExternalLogin = async () => {
  if (import.meta.server) return
  const route = useRoute()
  const router = useRouter()
  const tokenFromUrl = typeof route.query.tg_login === "string" ? route.query.tg_login.trim() : ""
  let tokenFromStorage = ""
  try {
    tokenFromStorage = sessionStorage.getItem("tg_web_login_token") || ""
  } catch {
    // Ignored
  }

  const token = tokenFromUrl || tokenFromStorage
  if (token && !user.value) {
    try {
      const res = await authApi.checkTelegramWebLogin(token, locale.value)
      if (res.data?.status === "SUCCESS") {
        try {
          sessionStorage.removeItem("tg_web_login_token")
        } catch {
          // Ignored
        }
        if (res.data.user) {
          setUser(res.data.user)
        }
        await load(true).catch(() => undefined)
        if (tokenFromUrl) {
          const query = { ...route.query }
          delete query.tg_login
          await router.replace({ query })
        }
      }
    } catch {
      // Ignored
    }
  }
}

onMounted(async () => {
  await initTMA()
  await checkExternalLogin()
})
</script>

<template>
  <NuxtLayout>
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </NuxtLayout>
</template>
