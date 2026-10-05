import { ApiRequestError } from "~/types/api"

export const cabinetErrorMessage = (error: unknown, fallback = "Amalni bajarib bo‘lmadi.") => {
  if (error instanceof ApiRequestError) return error.message
  return error instanceof Error ? error.message : fallback
}
