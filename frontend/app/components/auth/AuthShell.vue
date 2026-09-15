<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <main class="auth-shell">
    <section class="auth-panel">
      <header class="auth-header">
        <AppBrand />
        <AppUiPreferences />
      </header>

      <div class="auth-content">
        <h1>{{ title }}</h1>
        <slot />
      </div>
    </section>

    <div class="auth-visual" aria-hidden="true">
      <img src="/images/auth-gaming-club.png" alt="">
    </div>
  </main>
</template>
