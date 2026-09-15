export type ThemeMode = "light" | "dark"

export const useTheme = () => {
  const mode = useState<ThemeMode>("theme", () => "dark")

  const apply = () => {
    if (import.meta.client) document.documentElement.dataset.theme = mode.value
  }

  const setMode = (value: ThemeMode) => {
    mode.value = value
    if (import.meta.client) localStorage.setItem("theme", value)
    apply()
  }

  const toggle = () => setMode(mode.value === "dark" ? "light" : "dark")

  onMounted(() => {
    const saved = localStorage.getItem("theme") as ThemeMode | null
    const preferred = matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light"
    setMode(saved === "light" || saved === "dark" ? saved : preferred)
  })

  return { mode, setMode, toggle }
}
