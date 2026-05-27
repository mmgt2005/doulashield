'use client'

interface Props {
  onStayLoggedIn: () => void
}

export default function SessionTimeoutModal({ onStayLoggedIn }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm w-full mx-4 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Session expiring soon</h2>
        <p className="text-sm text-gray-600">
          You will be logged out in 60 seconds due to inactivity.
        </p>
        <button
          onClick={onStayLoggedIn}
          className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Stay logged in
        </button>
      </div>
    </div>
  )
}
