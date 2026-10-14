<script setup lang="ts">
import ClubForm from "~/components/cabinet/ClubForm.vue"

definePageMeta({
  alias: ["/site/staff/panel/clubs/new", "/site/client/panel/clubs/new"],
  layout: "admin",
  middleware: ["admin"],
})

const { isStaff: isPlatformAdmin } = useCabinetAccess()
const cabinetPath = useCabinetPath()
if (!isPlatformAdmin.value) await navigateTo(cabinetPath("/clubs"), { replace: true })
</script>

<template>
  <ClubForm v-if="isPlatformAdmin" />
</template>
