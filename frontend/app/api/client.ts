import type { FetchError, FetchOptions } from "ofetch"

import { ApiRequestError, type ApiErrorData } from "~/types/api"

type ApiOptions = FetchOptions & { local?: boolean, token?: string }

const isApiError = (value: unknown): value is ApiErrorData => {
  if (!value || typeof value !== "object") return false

  const data = value as Partial<ApiErrorData>
  return data.success === false
    && typeof data.code === "string"
    && typeof data.message === "string"
}

export const useApiClient = () => {
  const config = useRuntimeConfig()
  const requestFetch = useRequestFetch()

  const request = async <T>(path: string, options: ApiOptions = {}) => {
    const { local, token, headers, ...fetchOptions } = options
    const requestHeaders = new Headers(headers)
    if (token) requestHeaders.set("Authorization", `Bearer ${token}`)

    try {
      const fetcher = local ? requestFetch : $fetch
      return await fetcher<T>(path, {
        baseURL: local ? undefined : config.public.apiBaseUrl,
        ...fetchOptions,
        headers: requestHeaders,
      })
    } catch (error) {
      const fetchError = error as FetchError<ApiErrorData>
      if (isApiError(fetchError.data)) {
        throw new ApiRequestError(fetchError.data, fetchError.statusCode)
      }
      throw error
    }
  }

  return {
    request,
    get: <T>(path: string, options?: ApiOptions) =>
      request<T>(path, { ...options, method: "GET" }),
    post: <T>(path: string, options?: ApiOptions) =>
      request<T>(path, { ...options, method: "POST" }),
    patch: <T>(path: string, options?: ApiOptions) =>
      request<T>(path, { ...options, method: "PATCH" }),
    delete: <T>(path: string, options?: ApiOptions) =>
      request<T>(path, { ...options, method: "DELETE" }),
  }
}
