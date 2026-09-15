<script setup lang="ts">
definePageMeta({ middleware: "guest" })
const route = useRoute()
await navigateTo({ path: "/login", query: route.query })
</script>

<template>
  <div />
</template>
