'use client'

import { useState } from 'react'
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
  { href: '/admin/billing-providers', label: 'Billing Providers' },
  { href: '/admin/enrollment-services', label: 'Enrollment Services' },
  { href: '/admin/audit-logs', label: 'Audit Logs' },
]

const billingAdminLinks = [
  { href: '/billing-admin/claims', label: 'Agency Claims' },
  { href: '/billing-admin/settings', label: 'Agency Settings' },
]

interface SidebarProps {
  onClose?: () => void
}

export default function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname()
  const { user, logout } = useAuthStore()
  const [showGuide, setShowGuide] = useState(false)

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

  const links =
    user?.role === 'billing_admin'
      ? billingAdminLinks
      : user?.role === 'admin'
      ? [...providerLinks, ...adminLinks]
      : providerLinks

  const roleLabel =
    user?.role === 'admin' ? 'Admin' :
    user?.role === 'billing_admin' ? 'Billing Admin' :
    'Provider'

  const roleBadgeClass =
    user?.role === 'admin' ? 'bg-purple-100 text-purple-700' :
    user?.role === 'billing_admin' ? 'bg-teal-100 text-teal-700' :
    'bg-blue-100 text-blue-700'

  return (
    <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="px-4 py-4 border-b border-gray-200">
        <img src="/logo.png" alt="DoulaShield" className="w-36 h-auto" />
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
          {user?.role === 'admin' && (
            <Link
              href="/enrollment-admin-guide"
              onClick={onClose}
              className={`block px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                pathname === '/enrollment-admin-guide' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              }`}
            >
              Enrollment Guide
            </Link>
          )}
          {user?.role === 'billing_admin' && (
            <Link
              href="/billing-admin-guide"
              onClick={onClose}
              className={`block px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                pathname === '/billing-admin-guide' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              }`}
            >
              Billing Admin Guide
            </Link>
          )}
          {user?.is_demo && (
            <button
              onClick={() => { setShowGuide(true); onClose?.() }}
              className="block w-full text-left px-3 py-1.5 rounded text-xs font-medium text-green-700 hover:bg-green-50 transition-colors"
            >
              Walkthrough Guide
            </button>
          )}
        </div>
      </nav>

      {/* Walkthrough Guide modal */}
      {showGuide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setShowGuide(false)}
        >
          <div
            className="bg-white rounded-lg shadow-xl p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold text-gray-900">Walkthrough Guide</h3>
                <p className="text-xs text-gray-400 mt-0.5">Demo mode is on — claims are simulated and nothing goes to Availity</p>
              </div>
              <button onClick={() => setShowGuide(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4">×</button>
            </div>

            {/* Steps */}
            <div className="space-y-2 text-sm">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Workflow Steps</p>
              {[
                ['1', 'Add a client', 'Clients → Add Client. Use any name from the table below.'],
                ['2', 'Document a visit', 'Open the client → click a visit type (e.g. Prenatal 1) → Start Visit → End Visit → fill in SOAP notes.'],
                ['3', 'Collect MA 91 signature', 'Click "Collect MA 91 Signature" and sign on-screen, or test ZipZign with your own email.'],
                ['4', 'Submit claim', 'Click "Submit Claim". Demo Mode is on — simulated, nothing goes to Availity. Status shows as Processing.'],
                ['5', 'Explore Reports & Audit Packet', 'Go to Reports to see the claim. Open the visit and click "Download Audit Packet".'],
                ['6', 'Log payment (EOB)', 'Reports → Scan Remittance / EOB → upload the payment document to mark the claim as paid.'],
              ].map(([n, title, desc]) => (
                <div key={n} className="flex gap-3 rounded-lg border border-gray-200 p-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-bold text-gray-600 mt-0.5">{n}</span>
                  <div>
                    <p className="font-medium text-gray-800 text-xs">{title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
              <a
                href="/sample-eob.pdf"
                download="sample-remittance-advice.pdf"
                className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
              >
                <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                </svg>
                <span>Download Sample Remittance Advice (EOB) — use this in step 6 to practice uploading</span>
              </a>
            </div>

            {/* Sample SOAP */}
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

            {/* 10 patients */}
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
              <p className="text-xs text-gray-400">Patient 9 (FFS) demonstrates the manual billing path — download CMS 1500 and submit to the MCO portal directly.</p>
              <p className="text-xs text-gray-400 mt-1">Date of birth is optional — you can leave it blank or use the date picker widget to enter any date. The Referring NPI field does not appear on Add Client; leave it blank.</p>
            </div>

            <div className="flex justify-end pt-1">
              <button onClick={() => setShowGuide(false)} className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Close</button>
            </div>
          </div>
        </div>
      )}
      <div className="px-4 py-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 truncate">{user?.email}</p>
        {user?.role && (
          <span className={`mt-1 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeClass}`}>
            {roleLabel}
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
