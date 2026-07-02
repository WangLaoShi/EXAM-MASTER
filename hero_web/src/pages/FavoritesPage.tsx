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
      <div className="flex flex-col items-center justify-center gap-3 py-20">
        <Spinner size="lg" />
        <span className="text-default-500">加载收藏...</span>
      </div>
    )
  }

  if (error) {
    return <Alert status="danger">{getErrorMessage(error, '加载收藏失败')}</Alert>
  }

  const items = data?.favorites ?? []

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">收藏题目</h2>
        <p className="text-default-500">共 {data?.total ?? items.length} 条记录</p>
      </div>
      <div className="grid gap-4">
        {items.length > 0 ? (
          items.map((item) => (
            <Card key={item.id}>
              <Card.Header>
                <div className="flex items-center gap-2">
                  <Chip size="sm" color="warning" variant="soft">
                    收藏
                  </Chip>
                  <Chip size="sm" variant="secondary">
                    {item.question_type}
                  </Chip>
                </div>
              </Card.Header>
              <Card.Content>
                <RichContent content={item.question_stem || '暂无题干'} />
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
