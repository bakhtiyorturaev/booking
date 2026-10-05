<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faArrowRotateRight, faPlus, faPen, faTrash, faMagnifyingGlass, faStar, faLocationDot, faPhone, faCircleCheck, faCircleXmark } from "@fortawesome/free-solid-svg-icons"
const props = defineProps<{ name: string }>()
const icons = { refresh: faArrowRotateRight, plus: faPlus, edit: faPen, delete: faTrash, search: faMagnifyingGlass, star: faStar, location: faLocationDot, phone: faPhone, check: faCircleCheck, close: faCircleXmark }
const icon = computed(() => icons[props.name as keyof typeof icons] || faCircleCheck)
</script>
<template><FontAwesomeIcon :icon="icon" aria-hidden="true" /></template>
