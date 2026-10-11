import { useFavoritesApi } from "~/api/favorites"
import type { FavoriteItem } from "~/types/club"

const targetId = (item: FavoriteItem) => item.club?.id || item.barber?.id || ""

const LOCAL_STORAGE_KEY = "rezervuz_guest_favorite_ids"

export const useFavorites = () => {
  const auth = useAuth("customer")
  const favoritesApi = useFavoritesApi()
  const favoriteClubIds = useState<string[]>("favorite_club_ids_list", () => [])
  const favoritesList = useState<FavoriteItem[]>("favorites_items_list", () => [])
  const loading = useState<boolean>("favorites_loading", () => false)
  const initialized = useState<boolean>("favorites_initialized", () => false)
  const initializedFor = useState<string | null>("favorites_initialized_for", () => null)
  const pendingIds = useState<string[]>("favorites_pending_ids", () => [])
  const favoriteSet = computed(() => new Set(favoriteClubIds.value))

  const guestIds = (): string[] => {
    if (!import.meta.client) return []
    try {
      const value: unknown = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || "[]")
      return Array.isArray(value) ? value.filter((id): id is string => typeof id === "string") : []
    } catch { return [] }
  }
  const saveGuestIds = (ids: string[]) => {
    if (!import.meta.client) return
    try { localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(ids)) } catch { /* Storage can be unavailable. */ }
  }
  const waitForLoad = async () => {
    if (!loading.value) return
    await new Promise<void>((resolve) => {
      const stop = watch(loading, value => { if (!value) { stop(); resolve() } })
    })
  }
  const load = async (force = false) => {
    await waitForLoad()
    const identity = auth.user.value?.id || "guest"
    if (!force && initialized.value && initializedFor.value === identity) return
    loading.value = true
    if (initializedFor.value !== identity) {
      favoriteClubIds.value = []
      favoritesList.value = []
      initialized.value = false
    }
    try {
      if (auth.isAuthenticated.value) {
        let response = await favoritesApi.list()
        let items = response.results || []
        let page = 1
        while (response.next) {
          response = await favoritesApi.list({ page: ++page })
          items = [...items, ...response.results]
        }
        const remainingGuestIds: string[] = []
        for (const id of guestIds()) {
          if (items.some(item => targetId(item) === id)) continue
          try { items.push(await favoritesApi.add(id)) } catch { remainingGuestIds.push(id) }
        }
        if ((auth.user.value?.id || "guest") !== identity) return
        saveGuestIds(remainingGuestIds)
        favoritesList.value = items
        favoriteClubIds.value = [...new Set(items.map(item => targetId(item)))]
      } else {
        favoriteClubIds.value = guestIds()
        favoritesList.value = []
      }
      initializedFor.value = identity
      initialized.value = true
    } finally { loading.value = false }
  }
  const isFavorite = (clubId: string) => favoriteSet.value.has(clubId)
  const isPending = (clubId: string) => pendingIds.value.includes(clubId)
  const toggle = async (clubId: string) => {
    if (!clubId) return false
    await load()
    if (isPending(clubId)) return isFavorite(clubId)
    const wasFavorite = isFavorite(clubId)
    const previousItems = favoritesList.value.filter(item => targetId(item) === clubId)
    const identity = auth.user.value?.id || "guest"
    pendingIds.value = [...pendingIds.value, clubId]
    favoriteClubIds.value = wasFavorite
      ? favoriteClubIds.value.filter(id => id !== clubId)
      : [...favoriteClubIds.value, clubId]
    favoritesList.value = favoritesList.value.filter(item => targetId(item) !== clubId)
    try {
      if (auth.isAuthenticated.value) {
        if (wasFavorite) await favoritesApi.remove(clubId)
        else {
          const created = await favoritesApi.add(clubId)
          if ((auth.user.value?.id || "guest") === identity) favoritesList.value = [created, ...favoritesList.value]
        }
      } else saveGuestIds(favoriteClubIds.value)
      return !wasFavorite
    } catch (error) {
      if ((auth.user.value?.id || "guest") === identity) {
        favoriteClubIds.value = favoriteClubIds.value.filter(id => id !== clubId)
        if (wasFavorite) favoriteClubIds.value = [...favoriteClubIds.value, clubId]
        favoritesList.value = [...previousItems, ...favoritesList.value.filter(item => targetId(item) !== clubId)]
      }
      throw error
    } finally { pendingIds.value = pendingIds.value.filter(id => id !== clubId) }
  }
  const remove = async (id: string) => {
    await load()
    const item = favoritesList.value.find(item => item.id === id)
    const clubId = item ? targetId(item) : id
    if (isFavorite(clubId)) await toggle(clubId)
  }
  return { favoriteClubIds, favoritesList, loading, initialized, isFavorite, isPending, toggle, remove, load }
}
