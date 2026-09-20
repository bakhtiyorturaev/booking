import { useFavoritesApi } from "~/api/favorites"
import type { FavoriteItem } from "~/types/club"

const LOCAL_STORAGE_KEY = "bronla_favorite_club_ids"

export const useFavorites = () => {
  const auth = useAuth()
  const favoritesApi = useFavoritesApi()

  const favoriteClubIds = useState<string[]>("favorite_club_ids_list", () => [])
  const favoritesList = useState<FavoriteItem[]>("favorites_items_list", () => [])
  const loading = useState<boolean>("favorites_loading", () => false)
  const initialized = useState<boolean>("favorites_initialized", () => false)

  const favoriteSet = computed(() => new Set(favoriteClubIds.value))

  const saveToLocalStorage = (ids: string[]) => {
    if (import.meta.client) {
      try {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(ids))
      } catch {
        // Ignore localStorage errors
      }
    }
  }

  const loadFromLocalStorage = (): string[] => {
    if (import.meta.client) {
      try {
        const raw = localStorage.getItem(LOCAL_STORAGE_KEY)
        if (raw) {
          const parsed = JSON.parse(raw)
          if (Array.isArray(parsed)) return parsed
        }
      } catch {
        // Ignore localStorage errors
      }
    }
    return []
  }

  const load = async (force = false) => {
    if (initialized.value && !force) return
    loading.value = true

    // Load guest cached favorites first
    const cachedIds = loadFromLocalStorage()
    if (cachedIds.length && !favoriteClubIds.value.length) {
      favoriteClubIds.value = cachedIds
    }

    if (auth.isAuthenticated.value) {
      try {
        const res = await favoritesApi.list()
        favoritesList.value = res.results || []
        const serverIds = (res.results || []).map(f => f.club.id)
        
        // Merge with local cached IDs if any
        const combined = Array.from(new Set([...serverIds, ...cachedIds]))
        favoriteClubIds.value = combined
        saveToLocalStorage(combined)
      } catch {
        // Ignore loading errors
      }
    }
    initialized.value = true
    loading.value = false
  }

  const isFavorite = (clubId: string) => {
    if (!clubId) return false
    return favoriteSet.value.has(clubId)
  }

  const toggle = async (clubId: string) => {
    if (!clubId) return false
    const currentlyFav = favoriteSet.value.has(clubId)

    if (currentlyFav) {
      favoriteClubIds.value = favoriteClubIds.value.filter(id => id !== clubId)
      favoritesList.value = favoritesList.value.filter(item => item.club.id !== clubId && item.id !== clubId)
      saveToLocalStorage(favoriteClubIds.value)

      if (auth.isAuthenticated.value) {
        try {
          await favoritesApi.remove(clubId)
        } catch {
          // Silent fallback
        }
      }
      return false
    } else {
      favoriteClubIds.value = [...favoriteClubIds.value, clubId]
      saveToLocalStorage(favoriteClubIds.value)

      if (auth.isAuthenticated.value) {
        try {
          const created = await favoritesApi.add(clubId)
          if (created && created.id) {
            favoritesList.value = [created, ...favoritesList.value.filter(i => i.club.id !== clubId)]
          }
        } catch {
          // Silent fallback
        }
      }
      return true
    }
  }

  const remove = async (clubIdOrFavoriteId: string) => {
    return await toggle(clubIdOrFavoriteId)
  }

  return {
    favoriteClubIds,
    favoritesList,
    loading,
    initialized,
    isFavorite,
    toggle,
    remove,
    load,
  }
}
