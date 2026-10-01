<script setup lang="ts">
definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})
</script>

<template>
  <CabinetClubForm mode="create" base-path="/admin/clubs" />
</template>
