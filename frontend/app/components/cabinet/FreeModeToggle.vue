<script setup lang="ts">
import { useAdminApi } from "~/api/admin"
const props = defineProps<{ kind: "branch" | "barber"; id: string; isFree: boolean; name: string }>()
const emit = defineEmits<{ changed: [] }>()
const saving = ref(false)
const api = useAdminApi()
const change = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const checked = input.checked
  saving.value = true
  try {
    await api.setFreeMode(props.kind, props.id, checked)
    emit("changed")
    useToast().success(checked ? "Bepul rejim yoqildi." : "Pullik rejim yoqildi.")
  } catch (error) { input.checked = props.isFree; useToast().error(cabinetErrorMessage(error)) }
  finally { saving.value = false }
}
</script>
<template><label class="free-mode-control"><input type="checkbox" :checked="isFree" :disabled="saving" :aria-label="`${name}: bepul rejim`" @change="change"><span>{{ saving ? 'Saqlanmoqda…' : 'Bepul' }}</span></label></template>
<style scoped>
.free-mode-control { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; cursor: pointer; font-size: 13px; }
.free-mode-control input { width: 18px; height: 18px; accent-color: var(--primary); }
</style>
