<script setup lang="ts">
import AccountList from "~/components/cabinet/AccountList.vue"

definePageMeta({
  alias: ["/site/staff/panel/users/customers", "/site/client/panel/users/customers"],
  layout: "admin",
  middleware: ["admin"],
})
</script>

<template>
  <AccountList />
</template>
