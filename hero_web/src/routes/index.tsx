import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { BankDetailPage } from '@/pages/BankDetailPage'
import { BankListPage } from '@/pages/BankListPage'
import { ExamResultPage } from '@/pages/ExamResultPage'
import { ExamRoomPage } from '@/pages/ExamRoomPage'
import { FavoritesPage } from '@/pages/FavoritesPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { LoginPage, RegisterPage } from '@/pages/LoginPage'
import { WrongQuestionsPage } from '@/pages/WrongQuestionsPage'
import { ProtectedRoute } from '@/routes/ProtectedRoute'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/banks" replace />} />
          <Route path="banks" element={<BankListPage />} />
          <Route path="banks/:bankId" element={<BankDetailPage />} />
          <Route path="wrong" element={<WrongQuestionsPage />} />
          <Route path="favorites" element={<FavoritesPage />} />
          <Route path="history" element={<HistoryPage />} />
        </Route>
        <Route path="exam/:sessionId" element={<ExamRoomPage />} />
        <Route path="exam/:sessionId/result" element={<ExamResultPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/banks" replace />} />
    </Routes>
  )
}
