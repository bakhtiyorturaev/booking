import { useAdminApi } from "~/api/admin"

interface LocationDistrict {
  id: string
  name: string
  city: { id: string; name: string }
}

export const useCityDistricts = (cityId: () => string) => {
  const api = useAdminApi()
  const districts = ref<LocationDistrict[]>([])
  const isDistrictLoading = ref(false)
  const districtError = ref("")
  let version = 0

  watch(cityId, async city => {
    const requestVersion = ++version
    districts.value = []
    districtError.value = ""
    isDistrictLoading.value = Boolean(city)
    if (!city) return
    try {
      const response = await api.getDistricts(city)
      if (requestVersion !== version) return
      districts.value = response.results || response.data || response || []
    } catch (error) {
      if (requestVersion === version) districtError.value = cabinetErrorMessage(error)
    } finally {
      if (requestVersion === version) isDistrictLoading.value = false
    }
  }, { immediate: true })

  onBeforeUnmount(() => { version++ })
  return { districts, isDistrictLoading, districtError }
}
