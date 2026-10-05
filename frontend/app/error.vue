<script setup lang="ts">
import type { NuxtError } from "#app"

const props = defineProps<{ error: NuxtError }>()
const isNotFound = computed(() => props.error.statusCode === 404)
useHead({
  title: computed(() => isNotFound.value ? "404 — Page not found" : "Xatolik"),
  meta: [{ name: "robots", content: "noindex, nofollow" }],
})
</script>

<template>
  <main class="error-page">
    <img v-if="isNotFound" class="not-found-image" src="/images/not-found.svg" alt="404 — Page not found" width="686" height="286">
    <div v-else class="error-message">
      <h1>{{ error.statusCode }}</h1>
      <p>Sahifani yuklab bo‘lmadi.</p>
      <button type="button" @click="clearError({ redirect: '/' })">Bosh sahifaga qaytish</button>
    </div>
  </main>
</template>

<style scoped>
.error-page {
  box-sizing: border-box;
  display: grid;
  place-items: center;
  min-height: 100dvh;
  width: 100%;
  padding: 20px;
  background: #fff;
  color: #000;
}
.not-found-image { display: block; width: min(100%, 686px); height: auto; }
.error-message { text-align: center; }
.error-message h1 { margin: 0; font-size: 72px; font-weight: 400; }
.error-message p { margin: 8px 0 24px; font-size: 18px; }
.error-message button { padding: 12px 18px; border: 1px solid #ddd; border-radius: 8px; background: #fff; color: #000; cursor: pointer; }
</style>
