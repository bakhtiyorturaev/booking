export type ToastType = "success" | "error" | "warning" | "info"

export interface ToastItem {
  id: string
  message: string
  type: ToastType
  duration: number
  createdAt: number
}

const toastTimers = new Map<string, ReturnType<typeof setTimeout>>()

export const useToast = () => {
  const toasts = useState<ToastItem[]>("global_toast_items", () => [])

  const remove = (id: string) => {
    const timer = toastTimers.get(id)
    if (timer) {
      clearTimeout(timer)
      toastTimers.delete(id)
    }
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  const clear = () => {
    toastTimers.forEach(timer => clearTimeout(timer))
    toastTimers.clear()
    toasts.value = []
  }

  const show = (message: string, type: ToastType = "info", duration = 5000): string => {
    if (!message || !message.trim()) return ""

    // If identical message is already shown, refresh its timer
    const existing = toasts.value.find(t => t.message === message && t.type === type)
    if (existing) {
      const timer = toastTimers.get(existing.id)
      if (timer) clearTimeout(timer)
      const newTimer = setTimeout(() => {
        remove(existing.id)
      }, duration)
      toastTimers.set(existing.id, newTimer)
      return existing.id
    }

    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
    const newToast: ToastItem = {
      id,
      message: message.trim(),
      type,
      duration,
      createdAt: Date.now(),
    }

    // Limit to maximum 3 simultaneous toasts
    if (toasts.value.length >= 3) {
      const oldest = toasts.value[0]
      if (oldest) remove(oldest.id)
    }

    toasts.value.push(newToast)

    if (duration > 0) {
      const timer = setTimeout(() => {
        remove(id)
      }, duration)
      toastTimers.set(id, timer)
    }

    return id
  }

  const success = (message: string, duration = 5000) => show(message, "success", duration)
  const error = (message: string, duration = 5000) => show(message, "error", duration)
  const warning = (message: string, duration = 5000) => show(message, "warning", duration)
  const info = (message: string, duration = 5000) => show(message, "info", duration)

  return {
    toasts,
    show,
    success,
    error,
    warning,
    info,
    remove,
    clear,
  }
}
