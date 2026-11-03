<template>
  <NuxtLink class="brand" to="/">
    <span class="brand-mark" aria-hidden="true">
      <img src="/logo-mark.png" alt="" width="25" height="40">
    </span>
    <span class="brand-wordmark"><span class="brand-wordmark-title">Uzbekistan</span><span class="brand-wordmark-sub">Tour guide</span></span>
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
  display: inline-flex;
  width: auto;
  height: 2.5rem;
  border: 0;
  border-radius: 0;
  background: none;
}

.brand-mark img {
  width: auto;
  height: 100%;
}
</style>
