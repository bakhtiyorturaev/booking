<script setup lang="ts">
import { useTelegramWebApp } from "~/composables/useTelegramWebApp"

const { initTMA } = useTelegramWebApp()

onMounted(() => {
  void initTMA()
})
</script>

<template>
  <NuxtLayout>
    <NuxtRouteAnnouncer />
    <NuxtPage />
  </NuxtLayout>
</template>
