export const API_ROUTES = {
  login: '/api/v1/auth/login',
  refresh: '/api/v1/auth/refresh',
  logout: '/api/v1/auth/logout',
  mfaSetup: '/api/v1/auth/mfa/setup',
  mfaVerify: '/api/v1/auth/mfa/verify',
  patients: '/api/v1/patients',
  adminUsers: '/api/v1/admin/users',
  auditLogs: '/api/v1/admin/audit-logs',
} as const
