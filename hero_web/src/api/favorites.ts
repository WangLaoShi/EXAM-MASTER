import { apiClient } from '@/api/client'

export interface FavoriteItem {
  id: string
  question_id: string
  bank_id: string
  question_stem: string
  question_type: string
  note?: string | null
  created_at: string
}

export interface FavoriteListResult {
  favorites: FavoriteItem[]
  total: number
}

export async function fetchFavorites(params?: {
  skip?: number
  limit?: number
  bank_id?: string
}): Promise<FavoriteListResult> {
  const { data } = await apiClient.get<FavoriteListResult>('/favorites', { params })
  return data
}

export async function checkFavorite(questionId: string): Promise<boolean> {
  const { data } = await apiClient.get<{ is_favorite: boolean }>(`/favorites/check/${questionId}`)
  return data.is_favorite
}

export async function addFavorite(questionId: string, bankId: string): Promise<void> {
  await apiClient.post('/favorites', { question_id: questionId, bank_id: bankId })
}

export async function removeFavoriteByQuestion(questionId: string): Promise<void> {
  await apiClient.delete(`/favorites/question/${questionId}`)
}

export async function toggleFavorite(
  questionId: string,
  bankId: string,
  isFavorite: boolean,
): Promise<void> {
  if (isFavorite) {
    await removeFavoriteByQuestion(questionId)
  } else {
    await addFavorite(questionId, bankId)
  }
}
