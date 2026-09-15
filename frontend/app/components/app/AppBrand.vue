<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faBolt } from "@fortawesome/free-solid-svg-icons"
</script>

<template>
  <NuxtLink class="brand" to="/">
    <span class="brand-mark" aria-hidden="true">
      <FontAwesomeIcon :icon="faBolt" />
    </span>
    <span class="brand-text">
      <strong>Rezerv</strong><span class="brand-accent">UZ</span>
    </span>
  </NuxtLink>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text);
  transition: transform 0.2s ease;
}

.brand:hover {
  transform: translateY(-1px);
}

.brand-mark {
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  background: linear-gradient(135deg, #6366f1 0%, #3b82f6 100%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 0.9rem;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
}

.brand-text {
  letter-spacing: -0.02em;
}

.brand-accent {
  color: #6366f1;
  font-weight: 800;
  margin-left: 1px;
}
</style>
