/**
 * Access token is stored only in module memory (never localStorage/sessionStorage)
 * to protect against XSS. On page reload, the app calls /auth/refresh using the
 * httpOnly refresh-token cookie to obtain a new access token.
 */

let _accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  _accessToken = token
}

export function getAccessToken(): string | null {
  return _accessToken
}

export function clearAccessToken(): void {
  _accessToken = null
}
