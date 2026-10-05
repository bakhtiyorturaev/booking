<script setup lang="ts">
import TelegramAuthModal from "~/components/auth/TelegramAuthModal.vue"

definePageMeta({ middleware: "guest" })

const { t } = useTranslations()
useHead({
  title: computed(() => t("auth.login_tab") || "Kirish"),
})

const route = useRoute()
const showModal = ref(true)

const onAuthenticated = async () => {
  const requested = route.query.redirect
  const target = typeof requested === "string" && requested.startsWith("/") && !requested.startsWith("//") && !requested.includes("\\") && !requested.startsWith("/site/") && !requested.startsWith("/cabinet") ? requested : "/"
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
