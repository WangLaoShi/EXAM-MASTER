import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Chip, Spinner } from '@heroui/react'
import { fetchFavorites } from '@/api/favorites'
import { getErrorMessage } from '@/api/client'
import { RichContent } from '@/components/question/RichContent'

export function FavoritesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => fetchFavorites({ limit: 50 }),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return <Alert status="danger">{getErrorMessage(error, '加载收藏失败')}</Alert>
  }

  const items = data?.items ?? data?.favorites ?? data ?? []

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">收藏题目</h2>
        <p className="text-default-500">共 {Array.isArray(items) ? items.length : 0} 条记录</p>
      </div>
      <div className="grid gap-4">
        {Array.isArray(items) && items.length > 0 ? (
          items.map((item: Record<string, unknown>) => (
            <Card key={String(item.id)}>
              <Card.Header>
                <Chip size="sm" color="warning" variant="soft">
                  收藏
                </Chip>
              </Card.Header>
              <Card.Content>
                <RichContent content={String(item.question_stem ?? item.stem ?? '暂无题干')} />
              </Card.Content>
            </Card>
          ))
        ) : (
          <Alert status="default">暂无收藏</Alert>
        )}
      </div>
    </div>
  )
}
