import { useAuth } from "~/composables/useAuth"
import { useTranslations } from "~/composables/useTranslations"
import { useAuthApi } from "~/api/auth"

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData: string
        initDataUnsafe?: {
          user?: {
            id: number
            first_name: string
            last_name?: string
            username?: string
            language_code?: string
            photo_url?: string
          }
          auth_date?: number
          hash?: string
        }
        colorScheme?: "light" | "dark"
        themeParams?: Record<string, string>
        isExpanded?: boolean
        viewportHeight?: number
        viewportStableHeight?: number
        ready: () => void
        expand: () => void
        close: () => void
        enableClosingConfirmation: () => void
        disableClosingConfirmation: () => void
        MainButton: {
          text: string
          color: string
          textColor: string
          isVisible: boolean
          isActive: boolean
          isProgressVisible: boolean
          setText: (text: string) => void
          onClick: (fn: () => void) => void
          offClick: (fn: () => void) => void
          show: () => void
          hide: () => void
          enable: () => void
          disable: () => void
          showProgress: (leaveActive?: boolean) => void
          hideProgress: () => void
        }
        BackButton: {
          isVisible: boolean
          onClick: (fn: () => void) => void
          offClick: (fn: () => void) => void
          show: () => void
          hide: () => void
        }
        HapticFeedback: {
          impactOccurred: (
            style: "light" | "medium" | "heavy" | "rigid" | "soft",
          ) => void
          notificationOccurred: (type: "error" | "success" | "warning") => void
          selectionChanged: () => void
        }
        setHeaderColor: (color: string) => void
        setBackgroundColor: (color: string) => void
      }
    }
  }
}

export const useTelegramWebApp = () => {
  const { user, load, setUser } = useAuth()
  const { locale } = useTranslations()
  const authApi = useAuthApi()

  const isTMA = computed(() => {
    if (import.meta.server) return false
    return Boolean(window.Telegram?.WebApp?.initData)
  })

  const webApp = computed(() => {
    if (import.meta.server) return undefined
    return window.Telegram?.WebApp
  })

  const isAuthenticating = ref(false)

  const initTMA = async () => {
    if (import.meta.server) return
    const tg = window.Telegram?.WebApp
    if (!tg || !tg.initData) return

    try {
      tg.ready()
      tg.expand()
      tg.enableClosingConfirmation()
    } catch {
      // Telegram WebApp method error ignore
    }

    // Agar foydalanuvchi hali kirmagan bo'lsa va initData bo'lsa, avto-login qilamiz
    if (!user.value && !isAuthenticating.value) {
      isAuthenticating.value = true
      try {
        const response = await authApi.telegramMiniAppLogin(tg.initData, locale.value)
        setUser(response.data.user)
        await load(true)
        haptic("success")
      } catch {
        // Avto-login xatolik bo'lsa
      } finally {
        isAuthenticating.value = false
      }
    }
  }

  const haptic = (
    type: "light" | "medium" | "heavy" | "success" | "warning" | "error" = "light",
  ) => {
    if (import.meta.server) return
    const tg = window.Telegram?.WebApp
    if (!tg?.HapticFeedback) return

    try {
      if (type === "success" || type === "warning" || type === "error") {
        tg.HapticFeedback.notificationOccurred(type)
      } else {
        tg.HapticFeedback.impactOccurred(type)
      }
    } catch {
      // Ignored
    }
  }

  const setupMainButton = (text: string, onClick: () => void) => {
    const tg = window.Telegram?.WebApp
    if (!tg?.MainButton) return () => {}

    tg.MainButton.setText(text)
    tg.MainButton.show()
    tg.MainButton.onClick(onClick)

    return () => {
      tg.MainButton.offClick(onClick)
      tg.MainButton.hide()
    }
  }

  return {
    isTMA,
    webApp,
    initTMA,
    haptic,
    setupMainButton,
  }
}
