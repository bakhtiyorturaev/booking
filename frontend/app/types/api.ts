export interface ApiErrorData {
  success: false
  code: string
  message: string
  errors: unknown
}

export class ApiRequestError extends Error {
  readonly code: string
  readonly statusCode?: number
  readonly errors: unknown

  constructor(data: ApiErrorData, statusCode?: number) {
    super(data.message)
    this.name = "ApiRequestError"
    this.code = data.code
    this.statusCode = statusCode
    this.errors = data.errors
  }
}
