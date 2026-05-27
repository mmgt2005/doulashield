'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuthStore } from '@/store/auth-store'
import axios from 'axios'
import { clearAccessToken } from '@/lib/auth'

const providerLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/clients', label: 'Clients' },
]

const adminLinks = [
  { href: '/admin/users', label: 'Users' },
  { href: '/admin/audit-logs', label: 'Audit Logs' },
]

export default function Sidebar() {
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
    <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col">
      <div className="px-4 py-5 border-b border-gray-200">
        <span className="text-lg font-bold text-blue-700">DolaShield</span>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-1">
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`block px-3 py-2 rounded text-sm font-medium transition-colors ${
              pathname.startsWith(href)
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            {label}
          </Link>
        ))}
      </nav>
      <div className="px-4 py-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 truncate">{user?.email}</p>
        <button
          onClick={handleLogout}
          className="mt-2 text-xs text-red-600 hover:underline"
        >
          Sign out
        </button>
      </div>
    </aside>
  )
}
