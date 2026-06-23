'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'
import { User, UserWithBilling, BillingProvider } from '@/types/domain'

type MergedUser = User & Partial<Omit<UserWithBilling, keyof User>>

export default function AdminUsersPage() {
  const router = useRouter()
  const { user: currentUser, startImpersonation, priorSession } = useAuthStore()
  const [users, setUsers] = useState<MergedUser[]>([])
  const [billingProviders, setBillingProviders] = useState<BillingProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [actionToast, setActionToast] = useState<string | null>(null)
  const [linkModal, setLinkModal] = useState<{ userId: string; email: string } | null>(null)
  const [linkInput, setLinkInput] = useState('')
  const [linkError, setLinkError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [createEmail, setCreateEmail] = useState('')
  const [createFullName, setCreateFullName] = useState('')
  const [createRole, setCreateRole] = useState<'provider' | 'admin' | 'billing_admin'>('provider')
  const [createManagedBpId, setCreateManagedBpId] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [creating, setCreating] = useState<'only' | 'send' | false>(false)
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null)
  const [copied, setCopied] = useState(false)

  // Assign to agency modal
  const [assignModal, setAssignModal] = useState<{ userId: string; email: string; currentBpId: string | null } | null>(null)
  const [assignBpId, setAssignBpId] = useState('')
  const [assignError, setAssignError] = useState<string | null>(null)

  // Demo mode
  const [demoModal, setDemoModal] = useState<{ id: string; email: string; current: boolean } | null>(null)
  const [demoTogglingId, setDemoTogglingId] = useState<string | null>(null)
  const [guideModal, setGuideModal] = useState<string | null>(null)

  const headers = { Authorization: `Bearer ${getAccessToken()}` }
  const api = process.env.NEXT_PUBLIC_API_URL

  const showToast = (msg: string) => {
    setActionToast(msg)
    setTimeout(() => setActionToast(null), 4000)
  }

  const reload = async () => {
    const [usersRes, billingRes, bpRes] = await Promise.allSettled([
      axios.get<User[]>(`${api}/api/v1/admin/users`, { headers }),
      axios.get<UserWithBilling[]>(`${api}/api/v1/admin/billing/users`, { headers }),
      axios.get<BillingProvider[]>(`${api}/api/v1/admin/billing-providers`, { headers }),
    ])
    const baseUsers = usersRes.status === 'fulfilled' ? usersRes.value.data : []
    const billingMap = billingRes.status === 'fulfilled'
      ? Object.fromEntries(billingRes.value.data.map((u) => [u.id, u]))
      : {}
    setUsers(baseUsers.map((u) => ({ ...u, ...(billingMap[u.id] ?? {}) })))
    if (bpRes.status === 'fulfilled') setBillingProviders(bpRes.value.data)
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
      const msg = (axios.isAxiosError(e) && e.response?.data?.detail)
        ? e.response.data.detail
        : 'Failed to send welcome email'
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

  const openAssignModal = (userId: string, email: string, currentBpId: string | null) => {
    setAssignModal({ userId, email, currentBpId })
    setAssignBpId(currentBpId ?? '')
    setAssignError(null)
  }

  const submitAssign = async () => {
    if (!assignModal) return
    setActionLoading(`assign-${assignModal.userId}`)
    try {
      if (assignBpId) {
        await axios.post(
          `${api}/api/v1/admin/billing-providers/${assignBpId}/assign-provider`,
          { provider_user_id: assignModal.userId },
          { headers },
        )
      } else {
        // Unassign: patch billing_provider_id to null via admin users endpoint
        await axios.patch(
          `${api}/api/v1/admin/users/${assignModal.userId}`,
          { billing_provider_id: null },
          { headers },
        )
      }
      showToast(`Agency assignment updated for ${assignModal.email}`)
      setAssignModal(null)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to assign'
      setAssignError(String(msg))
    } finally {
      setActionLoading(null)
    }
  }

  const openCreateModal = () => {
    setCreateEmail('')
    setCreateFullName('')
    setCreateRole('provider')
    setCreateManagedBpId('')
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
        {
          email: createEmail.trim(),
          full_name: createFullName.trim() || null,
          role: createRole,
          ...(createRole === 'billing_admin' && createManagedBpId ? { managed_billing_provider_id: createManagedBpId } : {}),
        },
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
        {
          email: createEmail.trim(),
          full_name: createFullName.trim() || null,
          role: createRole,
          ...(createRole === 'billing_admin' && createManagedBpId ? { managed_billing_provider_id: createManagedBpId } : {}),
        },
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

  const handleViewAs = async (u: MergedUser) => {
    setActionLoading(`viewas-${u.id}`)
    try {
      const res = await axios.post<{ access_token: string; target_id: string; target_email: string; target_name: string | null }>(
        `${api}/api/v1/admin/users/${u.id}/impersonate`,
        {},
        { headers },
      )
      const targetUser: User = {
        id: res.data.target_id,
        email: res.data.target_email,
        role: u.role as User['role'],
        full_name: res.data.target_name,
        mfa_enabled: u.mfa_enabled,
        is_active: u.is_active,
        created_at: u.created_at,
        last_sign_in_at: u.last_sign_in_at,
        welcome_email_sent_at: u.welcome_email_sent_at,
        billing_provider_id: u.billing_provider_id ?? null,
        managed_billing_provider_id: null,
      }
      startImpersonation(targetUser, res.data.access_token)
      router.push('/dashboard')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to start impersonation'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggleDemo = async (userId: string, enable: boolean) => {
    setDemoTogglingId(userId)
    setDemoModal(null)
    try {
      await axios.patch(`${api}/api/v1/admin/users/${userId}`, { is_demo: enable }, { headers })
      showToast(`Demo mode ${enable ? 'enabled' : 'disabled'}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to update'
      showToast(`Error: ${msg}`)
    } finally {
      setDemoTogglingId(null)
    }
  }

  const bpNameMap = Object.fromEntries(billingProviders.map((bp) => [bp.id, bp.name]))

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
              {['Email', 'Role', 'Agency', 'MFA', 'Active', 'Joined', 'Last Emailed', 'Deposit', 'Balance', 'Subscription', 'Actions'].map((h) => (
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
              const agencyName = u.billing_provider_id ? (bpNameMap[u.billing_provider_id] ?? '—') : null

              return (
                <tr key={u.id}>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3 capitalize">{u.role}</td>
                  <td className="px-4 py-3">
                    {agencyName
                      ? <span className="text-xs font-medium text-teal-700">{agencyName}</span>
                      : <span className="text-gray-300 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3">{u.mfa_enabled ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3">{u.is_active ? 'Yes' : 'No'}</td>
                  <td className="px-4 py-3 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-sm whitespace-nowrap">
                    {u.welcome_email_sent_at
                      ? new Date(u.welcome_email_sent_at).toLocaleDateString()
                      : <span className="text-gray-400">—</span>}
                  </td>

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
                      {isProvider && billingProviders.length > 0 && (
                        <button
                          onClick={() => openAssignModal(u.id, u.email, u.billing_provider_id ?? null)}
                          className="rounded border border-teal-300 px-2 py-1 text-xs font-medium text-teal-700 hover:bg-teal-50 whitespace-nowrap"
                        >
                          Assign Agency
                        </button>
                      )}
                      {isProvider && (
                        <>
                          <button
                            onClick={() => setGuideModal(u.email)}
                            className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 whitespace-nowrap"
                          >
                            Walkthrough Guide
                          </button>
                          <button
                            onClick={() => setDemoModal({ id: u.id, email: u.email, current: u.is_demo ?? false })}
                            disabled={demoTogglingId === u.id}
                            className={`rounded border px-2 py-1 text-xs font-medium disabled:opacity-50 whitespace-nowrap ${
                              u.is_demo
                                ? 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100'
                                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
                            }`}
                          >
                            {demoTogglingId === u.id ? '…' : u.is_demo ? 'Demo On' : 'Demo Off'}
                          </button>
                        </>
                      )}
                      {(isProvider || u.role === 'admin') && u.id !== currentUser?.id && !priorSession && (
                        <button
                          onClick={() => handleViewAs(u)}
                          disabled={actionLoading === `viewas-${u.id}`}
                          className="rounded border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50 whitespace-nowrap"
                        >
                          {actionLoading === `viewas-${u.id}` ? '…' : 'View as'}
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

      {/* Create User modal */}
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
                      {(['provider', 'admin', 'billing_admin'] as const).map((r, i) => (
                        <button
                          key={r}
                          type="button"
                          onClick={() => { setCreateRole(r); if (r !== 'billing_admin') setCreateManagedBpId('') }}
                          className={`px-3 py-1.5 text-sm font-medium transition-colors ${i > 0 ? 'border-l border-gray-300' : ''} ${createRole === r ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
                        >
                          {r === 'billing_admin' ? 'Billing Admin' : r.charAt(0).toUpperCase() + r.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>
                  {createRole === 'billing_admin' && billingProviders.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Managed Agency</label>
                      <select
                        value={createManagedBpId}
                        onChange={(e) => setCreateManagedBpId(e.target.value)}
                        className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                      >
                        <option value="">— Select billing provider —</option>
                        {billingProviders.map((bp) => (
                          <option key={bp.id} value={bp.id}>{bp.name}</option>
                        ))}
                      </select>
                    </div>
                  )}
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

      {/* Assign to Agency modal */}
      {assignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Assign to Billing Agency</h3>
            <p className="text-sm text-gray-500">
              Assigning <strong>{assignModal.email}</strong> to a billing agency sets their CMS 1500 Box 33 billing entity.
            </p>
            <select
              value={assignBpId}
              onChange={(e) => setAssignBpId(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">— Unassigned (use own NPI) —</option>
              {billingProviders.map((bp) => (
                <option key={bp.id} value={bp.id}>{bp.name}{bp.group_npi ? ` (NPI: ${bp.group_npi})` : ''}</option>
              ))}
            </select>
            {assignError && <p className="text-xs text-red-600">{assignError}</p>}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setAssignModal(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={submitAssign}
                disabled={actionLoading?.startsWith('assign-')}
                className="rounded bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
              >
                {actionLoading?.startsWith('assign-') ? 'Saving…' : 'Save Assignment'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Demo Mode confirmation modal */}
      {demoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-base font-semibold text-gray-900">
              {demoModal.current ? 'Disable Demo Mode' : 'Enable Demo Mode'}
            </h3>
            <p className="text-sm text-gray-500">
              {demoModal.current
                ? `This re-enables real Availity submissions for ${demoModal.email}. Enable when they're ready for live billing.`
                : `While demo mode is on, claim submissions for ${demoModal.email} are simulated — nothing goes to Availity. Share the Walkthrough Guide to get them started.`
              }
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDemoModal(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleToggleDemo(demoModal.id, !demoModal.current)}
                className={`rounded px-4 py-2 text-sm font-medium text-white ${
                  demoModal.current ? 'bg-gray-600 hover:bg-gray-700' : 'bg-green-600 hover:bg-green-700'
                }`}
              >
                {demoModal.current ? 'Disable Demo Mode' : 'Enable Demo Mode'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Walkthrough Guide modal */}
      {guideModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setGuideModal(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold text-gray-900">Provider Walkthrough Guide</h3>
                <p className="text-xs text-gray-400 mt-0.5">Share this with {guideModal} to walk through the full workflow with demo data</p>
              </div>
              <button
                onClick={() => setGuideModal(null)}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4"
              >
                ×
              </button>
            </div>

            {/* Workflow steps */}
            <div className="space-y-2 text-sm">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Workflow Steps</p>
              {[
                ['1', 'Add a client', 'Go to Clients → Add Client. Use any name and data from the table below.'],
                ['2', 'Document a visit', 'Open the client → click a visit type (e.g. Prenatal 1) → Start Visit → End Visit → fill in SOAP notes using the sample below.'],
                ['3', 'Collect MA 91 signature', 'Click "Collect MA 91 Signature" and sign on-screen, or test ZipZign by sending to your own email.'],
                ['4', 'Submit claim', 'Click "Submit Claim". Demo Mode is on — the submission is simulated and nothing goes to Availity. Status will show as Processing.'],
                ['5', 'Explore Reports & Audit Packet', 'Go to Reports to see the claim in the pipeline. Open the visit and click "Download Audit Packet" to see the full 7-section PDF.'],
                ['6', 'Log payment (EOB)', 'When payment arrives, go to Reports → Scan Remittance / EOB → upload the payment document to mark the claim as paid.'],
              ].map(([n, title, desc]) => (
                <div key={n} className="flex gap-3 rounded-lg border border-gray-200 p-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600 mt-0.5">{n}</span>
                  <div>
                    <p className="font-medium text-gray-800 text-xs">{title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Sample SOAP notes */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sample SOAP Notes (Prenatal 1)</p>
              <div className="rounded-lg border border-gray-200 p-3 space-y-1.5 text-xs">
                {[
                  ['Subjective', 'First doula visit at 12 weeks. Morning sickness improving. Client interested in natural birth and breastfeeding support.'],
                  ['Objective', 'BP 118/72. Client alert and engaged. Reviewed birth preferences and prenatal nutrition.'],
                  ['Assessment', 'Low-risk pregnancy at 12 weeks progressing normally.'],
                  ['Plan', 'Provide birth education materials. Schedule Prenatal 2 at 20 weeks. Follow up on iron levels.'],
                ].map(([label, text]) => (
                  <div key={label}>
                    <span className="font-medium text-gray-500">{label}: </span>
                    <span className="text-gray-700">{text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 10 sample patients table */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">10 Sample Patients</p>
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      {['#', 'Name', 'Medicaid ID', 'MCO', 'DOB (optional)', 'Address', 'Referring NPI'].map((h) => (
                        <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {[
                      ['1', 'Jane Sample', '1234567890', 'AmeriHealth Caritas', '01/15/1992', '123 Main St, Philadelphia, PA 19103', '9999999999'],
                      ['2', 'Maria Rodriguez', '2345678901', 'UPMC For You', '11/22/1988', '456 Oak Ave, Pittsburgh, PA 15213', '9999999999'],
                      ['3', 'Ashley Williams', '3456789012', 'Keystone First', '07/08/1995', '789 Elm Rd, Allentown, PA 18101', '9999999999'],
                      ['4', 'Sarah Johnson', '4567890123', 'Geisinger Health Plan', '03/30/1990', '321 Pine St, Scranton, PA 18501', '9999999999'],
                      ['5', 'Emily Davis', '5678901234', 'Aetna Better Health', '09/12/1993', '654 Maple Ave, Harrisburg, PA 17101', '9999999999'],
                      ['6', 'Destiny Brown', '6789012345', 'Health Partners Plans', '05/05/1997', '987 Cedar Ln, Reading, PA 19601', '9999999999'],
                      ['7', 'Tamara Wilson', '7890123456', 'Highmark Wholecare', '12/28/1991', '147 Birch Way, Lancaster, PA 17601', '9999999999'],
                      ['8', 'Keisha Moore', '8901234567', 'UnitedHealthcare Community Plan', '02/14/1986', '258 Spruce St, Erie, PA 16501', '9999999999'],
                      ['9', 'Brianna Taylor', '9012345678', 'FFS', '08/22/1994', '369 Walnut Dr, York, PA 17401', '9999999999'],
                      ['10', 'Jasmine Anderson', '0123456789', 'AmeriHealth Caritas', '06/11/1989', '741 Chestnut Blvd, Bethlehem, PA 18015', '9999999999'],
                    ].map((row, i) => (
                      <tr key={row[0]} className={i % 2 === 1 ? 'bg-gray-50' : ''}>
                        {row.map((cell, j) => (
                          <td key={j} className="px-3 py-2 text-gray-700 whitespace-nowrap">{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400">Referring NPI 9999999999 is a recognizable placeholder. Patient 9 (FFS) demonstrates the manual billing path.</p>
              <p className="text-xs text-gray-400 mt-1">Date of birth is optional — providers can leave it blank or pick any date using the date picker. The Referring NPI column does not appear on the Add Client form; leave it blank.</p>
            </div>

            <div className="flex justify-end pt-1">
              <button
                onClick={() => setGuideModal(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
