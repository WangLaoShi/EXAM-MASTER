import { Navigate, Outlet } from 'react-router-dom'
import { Spinner } from '@heroui/react'
import { useAuthStore } from '@/stores/authStore'

export function ProtectedRoute() {
  const initialized = useAuthStore((state) => state.initialized)
  const token = useAuthStore((state) => state.token)

  if (!initialized) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <Spinner size="lg" />
        <span className="text-default-500">加载中...</span>
      </div>
    )
  }

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
