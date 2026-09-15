<script setup lang="ts">
import TelegramAuthModal from "~/components/auth/TelegramAuthModal.vue"

definePageMeta({ middleware: "guest" })

const route = useRoute()
const showModal = ref(true)

const onAuthenticated = async () => {
  const target = typeof route.query.redirect === "string" && route.query.redirect ? route.query.redirect : "/"
  await navigateTo(target)
}

const onClose = async () => {
  await navigateTo("/")
}
</script>

<template>
  <div class="login-page-container">
    <TelegramAuthModal
      v-model="showModal"
      @authenticated="onAuthenticated"
      @close="onClose"
    />
  </div>
</template>

<style scoped>
.login-page-container {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--page);
}
</style>
