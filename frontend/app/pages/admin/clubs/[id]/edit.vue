<script setup lang="ts">
definePageMeta({
  layout: "admin",
  middleware: ["admin"],
})

const route = useRoute()
const clubId = route.params.id as string
</script>

<template>
  <CabinetClubForm mode="edit" :club-id="clubId" base-path="/admin/clubs" />
</template>
