import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Chip, Spinner } from '@heroui/react'
import { fetchPracticeHistory } from '@/api/practice'
import { getErrorMessage } from '@/api/client'

export function HistoryPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['practice-history'],
    queryFn: () => fetchPracticeHistory({ limit: 50 }),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return <Alert status="danger">{getErrorMessage(error, '加载历史失败')}</Alert>
  }

  const records = data?.records ?? []

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">答题历史</h2>
        <p className="text-default-500">
          共 {data?.total ?? records.length} 条 · 正确率{' '}
          {typeof data?.accuracy_rate === 'number' ? `${data.accuracy_rate.toFixed(1)}%` : '—'}
        </p>
      </div>
      <div className="grid gap-3">
        {records.length > 0 ? (
          records.map((record: Record<string, unknown>) => (
            <Card key={String(record.id)}>
              <Card.Content className="flex flex-wrap items-center justify-between gap-3 py-4">
                <div>
                  <p className="font-medium">题目 {String(record.question_id)}</p>
                  <p className="text-sm text-default-500">
                    {String(record.created_at ?? '').replace('T', ' ').slice(0, 19)}
                  </p>
                </div>
                <Chip color={record.is_correct ? 'success' : 'danger'} variant="soft">
                  {record.is_correct ? '正确' : '错误'}
                </Chip>
              </Card.Content>
            </Card>
          ))
        ) : (
          <Alert status="default">暂无答题历史</Alert>
        )}
      </div>
    </div>
  )
}
