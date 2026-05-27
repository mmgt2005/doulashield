export interface TokenResponse {
  access_token: string
  token_type: string
  mfa_required?: boolean
}

export interface ApiError {
  status: number
  message: string
}
