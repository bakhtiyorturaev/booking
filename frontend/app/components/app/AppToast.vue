<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import {
  faCircleCheck,
  faCircleExclamation,
  faTriangleExclamation,
  faCircleInfo,
  faXmark,
} from "@fortawesome/free-solid-svg-icons"
import { useToast, type ToastType } from "~/composables/useToast"

const { toasts, remove } = useToast()

const getIcon = (type: ToastType) => {
  switch (type) {
    case "success":
      return faCircleCheck
    case "error":
      return faCircleExclamation
    case "warning":
      return faTriangleExclamation
    case "info":
    default:
      return faCircleInfo
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite" aria-atomic="true">
      <TransitionGroup name="toast-pop">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="toast-card"
          :class="`toast-${toast.type}`"
          role="alert"
          @click="remove(toast.id)"
        >
          <div class="toast-icon-box">
            <FontAwesomeIcon :icon="getIcon(toast.type)" class="toast-status-icon" />
          </div>

          <div class="toast-content">
            <p class="toast-message">{{ toast.message }}</p>
          </div>

          <button
            type="button"
            class="toast-close-btn"
            aria-label="Yopish"
            @click.stop="remove(toast.id)"
          >
            <FontAwesomeIcon :icon="faXmark" />
          </button>

          <div
            v-if="toast.duration > 0"
            class="toast-progress-bar"
            :style="{ animationDuration: `${toast.duration}ms` }"
          />
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: max(16px, env(safe-area-inset-top, 16px));
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999999;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: calc(100% - 32px);
  max-width: 480px;
  pointer-events: none;
}

.toast-card {
  pointer-events: auto;
  position: relative;
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px 14px;
  border-radius: 14px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow:
    0 16px 36px -4px rgba(0, 0, 0, 0.45),
    0 6px 14px -2px rgba(0, 0, 0, 0.25),
    0 0 0 1px rgba(255, 255, 255, 0.08);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
  user-select: none;
}

.toast-card:hover {
  transform: scale(1.015);
}

/* Status variants */
.toast-success {
  background: rgba(6, 78, 59, 0.92);
  border: 1px solid rgba(52, 211, 153, 0.45);
  color: #ecfdf5;
}
.toast-success .toast-status-icon {
  color: #34d399;
}
.toast-success .toast-progress-bar {
  background: #34d399;
}

.toast-error {
  background: rgba(127, 29, 29, 0.94);
  border: 1px solid rgba(248, 113, 113, 0.5);
  color: #fef2f2;
}
.toast-error .toast-status-icon {
  color: #f87171;
}
.toast-error .toast-progress-bar {
  background: #f87171;
}

.toast-warning {
  background: rgba(120, 53, 15, 0.93);
  border: 1px solid rgba(251, 191, 36, 0.45);
  color: #fffbeb;
}
.toast-warning .toast-status-icon {
  color: #fbbf24;
}
.toast-warning .toast-progress-bar {
  background: #fbbf24;
}

.toast-info {
  background: rgba(30, 58, 138, 0.93);
  border: 1px solid rgba(96, 165, 250, 0.45);
  color: #eff6ff;
}
.toast-info .toast-status-icon {
  color: #60a5fa;
}
.toast-info .toast-progress-bar {
  background: #60a5fa;
}

.toast-icon-box {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  padding-top: 1px;
  flex-shrink: 0;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-message {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  line-height: 1.4;
  word-break: break-word;
}

.toast-close-btn {
  background: transparent;
  border: none;
  color: inherit;
  opacity: 0.65;
  font-size: 0.95rem;
  cursor: pointer;
  padding: 2px 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: opacity 0.15s ease, background-color 0.15s ease;
  flex-shrink: 0;
}

.toast-close-btn:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.15);
}

.toast-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  width: 100%;
  opacity: 0.8;
  animation-name: progressCountdown;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
}

@keyframes progressCountdown {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}

/* Animations */
.toast-pop-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-pop-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 1, 1);
}

.toast-pop-enter-from {
  opacity: 0;
  transform: translateY(-24px) scale(0.92);
}

.toast-pop-leave-to {
  opacity: 0;
  transform: translateY(-16px) scale(0.92);
}
</style>
