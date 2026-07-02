import { Button, Chip } from '@heroui/react'

interface QuestionNavGridProps {
  questionIds: string[]
  currentQuestionId?: string
  answeredIds: Set<string>
  markedIds: Set<string>
  onJump: (index: number) => void
}

export function QuestionNavGrid({
  questionIds,
  currentQuestionId,
  answeredIds,
  markedIds,
  onJump,
}: QuestionNavGridProps) {
  return (
    <div className="grid grid-cols-5 gap-2 sm:grid-cols-6 lg:grid-cols-8">
      {questionIds.map((questionId, index) => {
        const isCurrent = questionId === currentQuestionId
        const isAnswered = answeredIds.has(questionId)
        const isMarked = markedIds.has(questionId)

        return (
          <Button
            key={questionId}
            size="sm"
            variant={
              isCurrent ? 'primary' : isMarked ? 'danger-soft' : isAnswered ? 'secondary' : 'outline'
            }
            onPress={() => onJump(index)}
          >
            {index + 1}
          </Button>
        )
      })}
      <div className="col-span-full mt-2 flex flex-wrap gap-2 text-xs text-default-500">
        <Chip size="sm" variant="secondary">
          当前
        </Chip>
        <Chip size="sm" variant="soft">
          已答
        </Chip>
        <Chip size="sm" color="warning" variant="soft">
          标记
        </Chip>
      </div>
    </div>
  )
}
