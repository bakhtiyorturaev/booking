import { useApiClient } from "~/api/client"

export interface ServiceTypeOption {
  id: string
  code: string
  name: string
  translations?: Partial<Record<"uz" | "ru" | "en", string>>
}

export const useServiceTypesApi = () => {
  const api = useApiClient()

  return {
    list: () => api.get<ServiceTypeOption[]>("/api/service-types", { local: true }),
  }
}
