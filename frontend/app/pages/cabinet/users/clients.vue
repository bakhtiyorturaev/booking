<script setup lang="ts">
import AccountList from "~/components/cabinet/AccountList.vue"

definePageMeta({
  alias: ["/site/staff/panel/users/clients", "/site/client/panel/users/clients"],
  layout: "admin",
  middleware: ["admin"],
})
</script>

<template>
  <AccountList />
</template>
