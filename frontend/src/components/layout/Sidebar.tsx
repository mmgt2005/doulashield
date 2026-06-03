'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/store/auth-store'
import axios from 'axios'
import { clearAccessToken } from '@/lib/auth'

const providerLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/clients', label: 'Clients' },
  { href: '/reports', label: 'Reports' },
  { href: '/settings', label: 'Settings' },
]

const adminLinks = [
  { href: '/admin/users', label: 'Users' },
  { href: '/admin/audit-logs', label: 'Audit Logs' },
]

interface SidebarProps {
  onClose?: () => void
}

export default function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/logout`,
        {},
        { withCredentials: true }
      )
    } finally {
      logout()
      window.location.href = '/login'
    }
  }

  const links = [...providerLinks, ...(user?.role === 'admin' ? adminLinks : [])]

  return (
    <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="px-4 py-5 border-b border-gray-200">
        <span className="text-lg font-bold text-blue-700">DoulaShield</span>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-1 flex flex-col">
        <div className="space-y-1">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={`block px-3 py-2 rounded text-sm font-medium transition-colors ${
                pathname.startsWith(href)
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
        <div className="mt-auto pt-3 border-t border-gray-100 space-y-0.5">
          <p className="px-3 pb-1 text-xs font-medium text-gray-400 uppercase tracking-wide">Help</p>
          <Link
            href="/manual"
            onClick={onClose}
            className={`block px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              pathname === '/manual' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
            }`}
          >
            User Manual
          </Link>
          {user?.role === 'admin' && (
            <Link
              href="/admin-guide"
              onClick={onClose}
              className={`block px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                pathname === '/admin-guide' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              }`}
            >
              Admin Guide
            </Link>
          )}
        </div>
      </nav>
      <div className="px-4 py-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 truncate">{user?.email}</p>
        {user?.role && (
          <span className={`mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            user.role === 'admin'
              ? 'bg-purple-100 text-purple-700'
              : 'bg-blue-100 text-blue-700'
          }`}>
            {user.role === 'admin' ? 'Admin' : 'Provider'}
          </span>
        )}
        <button
          onClick={handleLogout}
          className="mt-2 block text-xs text-red-600 hover:underline"
        >
          Sign out
        </button>
        <p className="mt-2 text-xs text-gray-400">v{process.env.NEXT_PUBLIC_APP_VERSION}</p>
      </div>
    </aside>
  )
}
