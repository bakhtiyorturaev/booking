<script setup lang="ts">
definePageMeta({
  layout: "owner",
  middleware: ["owner"],
})
</script>

<template>
  <CabinetClubForm mode="create" base-path="/cabinet/clubs" />
</template>
