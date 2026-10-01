<script setup lang="ts">
definePageMeta({
  layout: "owner",
  middleware: ["owner"],
})

const route = useRoute()
const clubId = route.params.id as string
</script>

<template>
  <CabinetClubForm mode="edit" :club-id="clubId" base-path="/cabinet/clubs" />
</template>
