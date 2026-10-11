<script setup lang="ts">
import type { ServiceTypeOption } from "~/api/serviceTypes"
import { serviceTreeOptions } from "~/utils/serviceTree"
const props = defineProps<{ modelValue: string[]; services: ServiceTypeOption[] }>()
const emit = defineEmits<{ (event: "update:modelValue", value: string[]): void }>()
const rows = computed(() => serviceTreeOptions(props.services))
const toggle = (id: string) => emit("update:modelValue", props.modelValue.includes(id)
  ? props.modelValue.filter(value => value !== id) : [...props.modelValue, id])
</script>
<template>
  <div class="service-checklist">
    <label v-for="service in rows" :key="service.id" class="service-choice" :style="{ paddingLeft: `${8 + service.depth * 18}px` }">
      <input type="checkbox" :checked="modelValue.includes(service.id)" @change="toggle(service.id)">
      <span>{{ service.depth ? '↳ ' : '' }}{{ service.name }}</span>
    </label>
  </div>
</template>
<style scoped>
.service-checklist { display: grid; gap: 2px; width: 100%; }
.service-choice { display: flex; align-items: center; gap: 8px; min-height: 36px; padding-block: 5px; border-radius: 8px; font-size: 13px; }
.service-choice:hover { background: var(--control); }
</style>
