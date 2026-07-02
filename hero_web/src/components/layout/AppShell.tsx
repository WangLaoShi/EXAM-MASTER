import { Link, Outlet, useNavigate } from 'react-router-dom'
import { Button, Header } from '@heroui/react'
import { env } from '@/config/env'
import { useAuthStore } from '@/stores/authStore'

export function AppShell() {
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  return (
    <div className="min-h-screen bg-background">
      <Header className="border-b border-default-200 bg-background/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <Link to="/banks" className="text-lg font-semibold text-foreground no-underline">
            {env.appTitle}
          </Link>
          <nav className="flex flex-wrap items-center gap-2">
            <Button variant="ghost" onPress={() => navigate('/banks')}>
              题库
            </Button>
            <Button variant="ghost" onPress={() => navigate('/wrong')}>
              错题
            </Button>
            <Button variant="ghost" onPress={() => navigate('/favorites')}>
              收藏
            </Button>
            <Button variant="ghost" onPress={() => navigate('/history')}>
              历史
            </Button>
            {user ? (
              <>
                <span className="hidden text-sm text-default-500 sm:inline">{user.username}</span>
                <Button
                  variant="outline"
                  onPress={async () => {
                    await logout()
                    navigate('/login')
                  }}
                >
                  退出
                </Button>
              </>
            ) : null}
          </nav>
        </div>
      </Header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
