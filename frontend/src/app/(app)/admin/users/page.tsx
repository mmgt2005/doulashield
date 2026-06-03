'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'
import { User, UserWithBilling } from '@/types/domain'

type MergedUser = User & Partial<Omit<UserWithBilling, keyof User>>

export default function AdminUsersPage() {
  const { user: currentUser } = useAuthStore()
  const [users, setUsers] = useState<MergedUser[]>([])
  const [loading, setLoading] = useState(true)
  const [actionToast, setActionToast] = useState<string | null>(null)
  const [linkModal, setLinkModal] = useState<{ userId: string; email: string } | null>(null)
  const [linkInput, setLinkInput] = useState('')
  const [linkError, setLinkError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [createEmail, setCreateEmail] = useState('')
  const [createFullName, setCreateFullName] = useState('')
  const [createRole, setCreateRole] = useState<'provider' | 'admin'>('provider')
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState<'only' | 'send' | false>(false)
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null)
  const [copied, setCopied] = useState(false)

  const headers = { Authorization: `Bearer ${getAccessToken()}` }
  const api = process.env.NEXT_PUBLIC_API_URL

  const showToast = (msg: string) => {
    setActionToast(msg)
    setTimeout(() => setActionToast(null), 4000)
  }

  const reload = async () => {
    const [usersRes, billingRes] = await Promise.allSettled([
      axios.get<User[]>(`${api}/api/v1/admin/users`, { headers }),
      axios.get<UserWithBilling[]>(`${api}/api/v1/admin/billing/users`, { headers }),
    ])
    const baseUsers = usersRes.status === 'fulfilled' ? usersRes.value.data : []
    const billingMap = billingRes.status === 'fulfilled'
      ? Object.fromEntries(billingRes.value.data.map((u) => [u.id, u]))
      : {}
    setUsers(baseUsers.map((u) => ({ ...u, ...(billingMap[u.id] ?? {}) })))
  }

  useEffect(() => {
    reload().finally(() => setLoading(false))
  }, [])

  const sendDepositEmail = async (userId: string, email: string) => {
    setActionLoading(`deposit-${userId}`)
    try {
      await axios.post(`${api}/api/v1/admin/billing/generate-deposit-link`, { provider_user_id: userId }, { headers })
      showToast(`Deposit email sent to ${email}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to send email'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const sendWelcomeEmail = async (userId: string, email: string) => {
    setActionLoading(`welcome-${userId}`)
    try {
      await axios.post(`${api}/api/v1/admin/billing/send-welcome-email`, { provider_user_id: userId }, { headers })
      showToast(`Welcome email sent to ${email}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to send welcome email'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const openLinkModal = (userId: string, email: string) => {
    setLinkModal({ userId, email })
    setLinkInput('')
    setLinkError(null)
  }

  const submitLinkCustomer = async () => {
    if (!linkModal || !linkInput.trim().startsWith('cus_')) {
      setLinkError('Enter a valid Stripe customer ID starting with cus_')
      return
    }
    setActionLoading(`link-${linkModal.userId}`)
    try {
      await axios.post(
        `${api}/api/v1/admin/billing/link-stripe-customer`,
        { provider_user_id: linkModal.userId, stripe_customer_id: linkInput.trim() },
        { headers },
      )
      showToast(`Stripe customer linked for ${linkModal.email}`)
      setLinkModal(null)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to link'
      setLinkError(String(msg))
    } finally {
      setActionLoading(null)
    }
  }

  const startSubscription = async (userId: string, email: string) => {
    setActionLoading(`sub-${userId}`)
    try {
      await axios.post(`${api}/api/v1/admin/billing/start-subscription`, { provider_user_id: userId }, { headers })
      showToast(`Subscription started for ${email}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to start subscription'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const toggleActive = async (userId: string, email: string, currentActive: boolean) => {
    setActionLoading(`active-${userId}`)
    try {
      await axios.patch(`${api}/api/v1/admin/users/${userId}`, { is_active: !currentActive }, { headers })
      showToast(`${email} ${!currentActive ? 'reactivated' : 'deactivated'}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to update'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const toggleRole = async (userId: string, email: string, currentRole: string) => {
    const newRole = currentRole === 'admin' ? 'provider' : 'admin'
    setActionLoading(`role-${userId}`)
    try {
      await axios.patch(`${api}/api/v1/admin/users/${userId}`, { role: newRole }, { headers })
      showToast(`${email} is now ${newRole}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to update role'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const openCreateModal = () => {
    setCreateEmail('')
    setCreateFullName('')
    setCreateRole('provider')
    setCreateError(null)
    setCredentials(null)
    setCopied(false)
    setShowCreate(true)
  }

  const closeCreateModal = () => {
    setShowCreate(false)
    setCredentials(null)
    setCopied(false)
    reload()
  }

  const submitCreateAndSend = async () => {
    if (!createEmail.trim()) {
      setCreateError('Email is required')
      return
    }
    setCreating('send')
    setCreateError(null)
    try {
      await axios.post(
        `${api}/api/v1/admin/billing/create-and-invite`,
        { email: createEmail.trim(), full_name: createFullName.trim() || null, role: createRole },
        { headers },
      )
      setShowCreate(false)
      showToast(`Account created — welcome email sent to ${createEmail.trim()}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to create account'
      setCreateError(String(msg))
    } finally {
      setCreating(false)
    }
  }

  const submitCreateOnly = async () => {
    if (!createEmail.trim()) {
      setCreateError('Email is required')
      return
    }
    setCreating('only')
    setCreateError(null)
    try {
      const res = await axios.post<{ user_id: string; email: string; temp_password: string }>(
        `${api}/api/v1/admin/billing/create-account-only`,
        { email: createEmail.trim(), full_name: createFullName.trim() || null, role: createRole },
        { headers },
      )
      setCredentials({ email: res.data.email, password: res.data.temp_password })
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to create account'
      setCreateError(String(msg))
    } finally {
      setCreating(false)
    }
  }

  const copyPassword = async () => {
    if (!credentials) return
    try {
      await navigator.clipboard.writeText(credentials.password)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // fallback: select text
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Users</h1>
        <button
          onClick={openCreateModal}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Add User
        </button>
      </div>

      {actionToast && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-800">
          {actionToast}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Email', 'Role', 'MFA', 'Active', 'Joined', 'Deposit', 'Balance', 'Subscription', 'Actions'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {users.map((u) => {
              const isProvider = u.role === 'provider'
              const depositPaid = u.deposit_paid ?? false
              const subStatus = u.subscription_status ?? null
              const balance = u.escrow_balance_remaining ?? 400
              const subActive = subStatus === 'active' || subStatus === 'trialing'

              return (
                <tr key={u.id}>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3 capitalize">{u.role}</td>
                  <td className="px-4 py-3">{u.mfa_enabled ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3">{u.is_active ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>

                  {/* Deposit */}
                  <td className="px-4 py-3">
                    {!isProvider ? <span className="text-gray-300">—</span> : depositPaid ? (
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">✓ Paid</span>
                    ) : u.stripe_customer_id ? (
                      <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Pending</span>
                    ) : (
                      <span className="text-gray-400 text-xs">—</span>
                    )}
                  </td>

                  {/* Balance */}
                  <td className="px-4 py-3">
                    {!isProvider ? <span className="text-gray-300">—</span> : balance > 0 ? (
                      <span className="text-xs text-gray-700">${Number(balance).toFixed(2)}</span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Cleared</span>
                    )}
                  </td>

                  {/* Subscription */}
                  <td className="px-4 py-3">
                    {!isProvider ? <span className="text-gray-300">—</span> : subActive ? (
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Active</span>
                    ) : subStatus === 'past_due' ? (
                      <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Past Due</span>
                    ) : subStatus === 'canceled' ? (
                      <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Canceled</span>
                    ) : (
                      <span className="text-gray-400 text-xs">None</span>
                    )}
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {!u.last_sign_in_at && u.id !== currentUser?.id && (
                        <button
                          onClick={() => sendWelcomeEmail(u.id, u.email)}
                          disabled={actionLoading === `welcome-${u.id}`}
                          className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
                        >
                          {actionLoading === `welcome-${u.id}` ? 'Sending…' : 'Send Welcome Email'}
                        </button>
                      )}
                      {isProvider && !depositPaid && (
                        <button
                          onClick={() => sendDepositEmail(u.id, u.email)}
                          disabled={actionLoading === `deposit-${u.id}`}
                          className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap"
                        >
                          {actionLoading === `deposit-${u.id}` ? 'Sending…' : 'Send Deposit Email'}
                        </button>
                      )}
                      {isProvider && !depositPaid && (
                        <button
                          onClick={() => openLinkModal(u.id, u.email)}
                          className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 whitespace-nowrap"
                        >
                          Link Customer ID
                        </button>
                      )}
                      {isProvider && depositPaid && !subActive && (
                        <button
                          onClick={() => startSubscription(u.id, u.email)}
                          disabled={actionLoading === `sub-${u.id}`}
                          className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                        >
                          {actionLoading === `sub-${u.id}` ? 'Starting…' : 'Start Subscription'}
                        </button>
                      )}
                      {u.id !== currentUser?.id && (
                        <button
                          onClick={() => toggleActive(u.id, u.email, u.is_active)}
                          disabled={actionLoading === `active-${u.id}`}
                          className={`rounded px-2 py-1 text-xs font-medium disabled:opacity-50 whitespace-nowrap ${
                            u.is_active
                              ? 'border border-red-300 text-red-600 hover:bg-red-50'
                              : 'border border-green-300 text-green-600 hover:bg-green-50'
                          }`}
                        >
                          {actionLoading === `active-${u.id}` ? '…' : u.is_active ? 'Deactivate' : 'Reactivate'}
                        </button>
                      )}
                      {u.id !== currentUser?.id && (
                        <button
                          onClick={() => toggleRole(u.id, u.email, u.role)}
                          disabled={actionLoading === `role-${u.id}`}
                          className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 whitespace-nowrap"
                        >
                          {actionLoading === `role-${u.id}` ? '…' : u.role === 'admin' ? 'Make Provider' : 'Make Admin'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Create Provider modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            {credentials ? (
              /* One-time credential display */
              <>
                <h3 className="text-base font-semibold text-gray-900">Account Created</h3>
                <p className="text-sm text-gray-500">
                  Share these credentials securely with the provider.
                </p>
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-2">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-gray-500 w-16 shrink-0">Email</span>
                    <span className="text-sm font-medium text-gray-900 flex-1">{credentials.email}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs text-gray-500 w-16 shrink-0">Password</span>
                    <span className="text-sm font-semibold font-mono text-gray-900 flex-1 select-all">{credentials.password}</span>
                  </div>
                </div>
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-2">
                  ⚠ Save this password — it will not be shown again.
                </p>
                <div className="flex justify-between gap-3">
                  <button
                    onClick={copyPassword}
                    className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    {copied ? '✓ Copied' : 'Copy Password'}
                  </button>
                  <button
                    onClick={closeCreateModal}
                    className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    Done
                  </button>
                </div>
              </>
            ) : (
              /* Create form */
              <>
                <h3 className="text-base font-semibold text-gray-900">Create Account</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                    <div className="flex rounded border border-gray-300 overflow-hidden w-fit">
                      <button
                        type="button"
                        onClick={() => setCreateRole('provider')}
                        className={`px-4 py-1.5 text-sm font-medium transition-colors ${createRole === 'provider' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                      >
                        Provider
                      </button>
                      <button
                        type="button"
                        onClick={() => setCreateRole('admin')}
                        className={`px-4 py-1.5 text-sm font-medium transition-colors border-l border-gray-300 ${createRole === 'admin' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                      >
                        Admin
                      </button>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="create-email" className="block text-sm font-medium text-gray-700">Email *</label>
                    <input
                      id="create-email"
                      type="email"
                      value={createEmail}
                      onChange={(e) => setCreateEmail(e.target.value)}
                      placeholder="user@example.com"
                      className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="create-name" className="block text-sm font-medium text-gray-700">Full name</label>
                    <input
                      id="create-name"
                      type="text"
                      value={createFullName}
                      onChange={(e) => setCreateFullName(e.target.value)}
                      placeholder="Jane Smith (optional)"
                      className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>
                {createError && <p className="text-xs text-red-600">{createError}</p>}
                <div className="flex items-center justify-between gap-3 pt-1">
                  <button
                    onClick={() => setShowCreate(false)}
                    disabled={creating !== false}
                    className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <div className="flex gap-2">
                    <button
                      onClick={submitCreateOnly}
                      disabled={creating !== false}
                      className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {creating === 'only' ? 'Creating…' : 'Create Account Only'}
                    </button>
                    <button
                      onClick={submitCreateAndSend}
                      disabled={creating !== false}
                      className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {creating === 'send' ? 'Creating…' : 'Create & Send Email'}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Link Customer ID modal */}
      {linkModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Link Stripe Customer ID</h3>
            <p className="text-sm text-gray-500">
              For <strong>{linkModal.email}</strong> — use this when their deposit was collected outside Stripe.
              Find the customer in the Stripe Dashboard and paste their ID below.
            </p>
            <input
              type="text"
              value={linkInput}
              onChange={(e) => setLinkInput(e.target.value)}
              placeholder="cus_..."
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {linkError && <p className="text-xs text-red-600">{linkError}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setLinkModal(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={submitLinkCustomer}
                disabled={actionLoading?.startsWith('link-')}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading?.startsWith('link-') ? 'Linking…' : 'Link Customer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
