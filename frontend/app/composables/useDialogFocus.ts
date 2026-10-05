import type { Ref } from "vue"

export const useDialogFocus = (open: Ref<boolean>, selector: string, onClose: () => void) => {
  let previousFocus: HTMLElement | null = null
  let previousOverflow = ""
  let listening = false
  const onKeydown = (event: KeyboardEvent) => {
    if (!open.value) return
    if (event.key === "Escape") { event.preventDefault(); onClose(); return }
    if (event.key !== "Tab") return
    const dialog = document.querySelector<HTMLElement>(selector)
    const controls = Array.from(dialog?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]') || []).filter(element => element.getClientRects().length)
    const first = controls[0]
    const last = controls.at(-1)
    if (!first || !last) { event.preventDefault(); dialog?.focus(); return }
    if (event.shiftKey && (document.activeElement === first || !dialog?.contains(document.activeElement))) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && (document.activeElement === last || !dialog?.contains(document.activeElement))) { event.preventDefault(); first.focus() }
  }
  const cleanup = () => {
    if (!listening) return
    document.removeEventListener("keydown", onKeydown)
    document.body.style.overflow = previousOverflow
    listening = false
    previousFocus?.focus()
  }
  watch(open, async (visible) => {
    if (!import.meta.client) return
    if (!visible) { cleanup(); return }
    previousFocus = document.activeElement as HTMLElement | null
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    document.addEventListener("keydown", onKeydown)
    listening = true
    await nextTick()
    document.querySelector<HTMLElement>(`${selector} input, ${selector} select, ${selector} button`)?.focus()
  }, { flush: "post", immediate: true })
  onBeforeUnmount(cleanup)
}
