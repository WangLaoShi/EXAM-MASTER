import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Chip, Spinner } from '@heroui/react'
import { fetchWrongQuestions } from '@/api/wrongQuestions'
import { getErrorMessage } from '@/api/client'
import { RichContent } from '@/components/question/RichContent'

export function WrongQuestionsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['wrong-questions'],
    queryFn: () => fetchWrongQuestions({ limit: 50 }),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return <Alert status="danger">{getErrorMessage(error, '加载错题失败')}</Alert>
  }

  const items = data?.items ?? data?.wrong_questions ?? data ?? []

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">错题本</h2>
        <p className="text-default-500">共 {Array.isArray(items) ? items.length : 0} 条记录</p>
      </div>
      <div className="grid gap-4">
        {Array.isArray(items) && items.length > 0 ? (
          items.map((item: Record<string, unknown>) => (
            <Card key={String(item.id)}>
              <Card.Header>
                <div className="flex items-center gap-2">
                  <Chip size="sm">{String(item.question_type ?? '题目')}</Chip>
                  <Chip size="sm" color="danger" variant="soft">
                    错 {String(item.error_count ?? 1)} 次
                  </Chip>
                </div>
              </Card.Header>
              <Card.Content>
                <RichContent content={String(item.question_stem ?? item.stem ?? '暂无题干')} />
              </Card.Content>
            </Card>
          ))
        ) : (
          <Alert status="default">暂无错题记录</Alert>
        )}
      </div>
    </div>
  )
}
