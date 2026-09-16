import { useToast, type ToastType } from "~/composables/useToast"

export const useTimedMessage = (duration = 5000) => {
  const message = ref("")
  let timer: ReturnType<typeof setTimeout> | undefined
  const toast = useToast()

  const clear = () => {
    if (timer) clearTimeout(timer)
    message.value = ""
  }

  const show = (value: string, type: ToastType = "info") => {
    clear()
    message.value = value
    if (value && value.trim()) {
      toast.show(value, type, duration)
    }
    timer = setTimeout(clear, duration)
  }

  const success = (value: string) => show(value, "success")
  const error = (value: string) => show(value, "error")
  const warning = (value: string) => show(value, "warning")
  const info = (value: string) => show(value, "info")

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return { message, show, success, error, warning, info, clear }
}
