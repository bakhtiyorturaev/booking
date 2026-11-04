<template>
  <NuxtLink class="brand" to="/">
    <span class="brand-mark" aria-hidden="true">
      <img src="/logo-mark.png" alt="" width="36" height="36">
    </span>
    <span class="brand-wordmark">Rezerv<span class="brand-wordmark-accent">uz.uz</span></span>
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
  border: 0;
  border-radius: 0.5rem;
  background: #00071f;
  display: inline-flex;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
}

.brand-mark img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
