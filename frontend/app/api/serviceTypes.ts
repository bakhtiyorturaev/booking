import { useApiClient } from "~/api/client"

export interface ServiceTypeOption {
  id: string
  code: string
  name: string
  translations?: Partial<Record<"uz" | "ru" | "en", string>>
  parent?: string | null
}

export interface ServiceTypeManagementItem extends ServiceTypeOption {
  name_ru: string
  name_en: string
  is_active: boolean
  sort_order: number
}

export const useServiceTypesApi = () => {
  const api = useApiClient()

  return {
    list: () => api.get<ServiceTypeOption[]>("/api/service-types", { local: true }),
  }
}
