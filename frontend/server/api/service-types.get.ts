import { djangoRequest, proxyDjangoError } from "~~/server/utils/django"
import type { ServiceTypeOption } from "~~/app/api/serviceTypes"

export default defineEventHandler(async (event): Promise<unknown> => {
  try {
    return await djangoRequest<ServiceTypeOption[]>(event, "/service-types/")
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
