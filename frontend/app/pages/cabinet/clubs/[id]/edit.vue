<script setup lang="ts">
import ClubForm from "~/components/cabinet/ClubForm.vue"

definePageMeta({
  alias: ["/site/staff/panel/clubs/:id()/edit", "/site/client/panel/clubs/:id()/edit"],
  layout: "admin",
  middleware: ["admin"],
})

const route = useRoute()
const clubId = computed(() => String(route.params.id))
const { isStaff: isPlatformAdmin } = useCabinetAccess()
const cabinetPath = useCabinetPath()
if (!isPlatformAdmin.value) await navigateTo(cabinetPath("/clubs"), { replace: true })
</script>

<template>
  <ClubForm v-if="isPlatformAdmin" :key="clubId" :club-id="clubId" />
</template>
