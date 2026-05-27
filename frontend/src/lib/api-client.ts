import axios, { AxiosError, AxiosInstance } from 'axios'
import { ApiError } from '@/types/api'

function getGenericMessage(status: number): string {
  const messages: Record<number, string> = {
    400: 'Invalid request. Please check your input.',
    401: 'Session expired. Please log in again.',
    403: 'You do not have permission to perform this action.',
    404: 'Record not found.',
    429: 'Too many requests. Please wait a moment.',
    500: 'An unexpected error occurred. Please try again.',
  }
  return messages[status] ?? 'An error occurred.'
}

function createApiClient(getAccessToken: () => string | null): AxiosInstance {
  const client = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    withCredentials: true, // needed to send/receive httpOnly refresh-token cookie
  })

  client.interceptors.request.use((config) => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (res) => res,
    (error: AxiosError) => {
      // Strip the response body — it may contain PHI or internal details.
      // Surface only a generic message keyed on status code.
      const safeError: ApiError = {
        status: error.response?.status ?? 0,
        message: getGenericMessage(error.response?.status ?? 0),
      }
      return Promise.reject(safeError)
    }
  )

  return client
}

export { createApiClient }
