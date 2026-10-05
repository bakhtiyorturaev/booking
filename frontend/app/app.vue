<script setup lang="ts">
import { authScopeForPath } from "~~/shared/authScope"
const { initTMA } = useTelegramWebApp()
const route = useRoute()
onMounted(async () => {
  if (authScopeForPath(route.path) === "customer") await initTMA()
})
</script>

<template>
  <NuxtLayout :key="authScopeForPath(route.path)">
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </NuxtLayout>
  <AppToast />
</template>
