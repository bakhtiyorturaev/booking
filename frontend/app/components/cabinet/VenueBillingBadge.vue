<script setup lang="ts">
import type { VenueBillingStatus } from "~/types/venueBilling"
import { useVenueBillingStatus } from "~/composables/useVenueBillingStatus"
const props = defineProps<{ billing: VenueBillingStatus; clubId?: string }>()
const statuses = useState<Record<string, VenueBillingStatus>>("venue-billing-statuses", () => ({}))
const current = computed(() => props.clubId ? statuses.value[props.clubId] || props.billing : props.billing)
const { level, label, expires } = useVenueBillingStatus(() => current.value)
</script>

<template>
  <div class="venue-billing-badge" :class="[level.toLowerCase(), { configured: Boolean(current.paid_until) }]" :data-alert-level="level">
    <strong>{{ label }}</strong><small v-if="expires">{{ expires }} gacha</small>
  </div>
</template>

<style scoped>
.venue-billing-badge { display: inline-flex; flex-direction: column; gap: 4px; padding: 9px 11px; border-radius: 8px; background: var(--control); color: var(--muted); max-width: 100%; font-variant-numeric: tabular-nums; }
.venue-billing-badge strong { font-size: 12px; font-weight: 650; }
.venue-billing-badge small { font-size: 10px; line-height: 1.4; }
.venue-billing-badge.configured { background: var(--success-soft); color: var(--success); }
.venue-billing-badge.warning { background: var(--warning-soft); color: var(--warning); }
.venue-billing-badge:is(.critical, .expired) { background: var(--danger-soft); color: var(--danger); }
</style>
