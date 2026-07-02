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
      <div className="flex flex-col items-center justify-center gap-3 py-20">
        <Spinner size="lg" />
        <span className="text-default-500">加载错题...</span>
      </div>
    )
  }

  if (error) {
    return <Alert status="danger">{getErrorMessage(error, '加载错题失败')}</Alert>
  }

  const items = data?.wrong_questions ?? []

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-2xl font-semibold">错题本</h2>
        <p className="text-default-500">
          共 {data?.total ?? items.length} 条 · 未订正 {data?.uncorrected_count ?? 0} 条
        </p>
      </div>
      <div className="grid gap-4">
        {items.length > 0 ? (
          items.map((item) => (
            <Card key={item.id}>
              <Card.Header>
                <div className="flex items-center gap-2">
                  <Chip size="sm" variant="secondary">
                    {item.question_type}
                  </Chip>
                  <Chip size="sm" color="danger" variant="soft">
                    错 {item.error_count} 次
                  </Chip>
                  {item.corrected ? (
                    <Chip size="sm" color="success" variant="soft">
                      已订正
                    </Chip>
                  ) : null}
                </div>
              </Card.Header>
              <Card.Content>
                <RichContent content={item.question_stem || '暂无题干'} />
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
