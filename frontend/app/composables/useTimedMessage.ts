export const useTimedMessage = (duration = 5000) => {
  const message = ref("")
  let timer: ReturnType<typeof setTimeout> | undefined

  const clear = () => {
    if (timer) clearTimeout(timer)
    message.value = ""
  }

  const show = (value: string) => {
    clear()
    message.value = value
    timer = setTimeout(clear, duration)
  }

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return { message, show, clear }
}
