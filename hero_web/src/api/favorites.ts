import { apiClient } from '@/api/client'

export async function fetchFavorites(params?: { skip?: number; limit?: number; bank_id?: string }) {
  const { data } = await apiClient.get('/favorites', { params })
  return data
}

export async function toggleFavorite(questionId: string, bankId: string): Promise<void> {
  await apiClient.post('/favorites', { question_id: questionId, bank_id: bankId })
}

export async function removeFavorite(favoriteId: string): Promise<void> {
  await apiClient.delete(`/favorites/${favoriteId}`)
}
