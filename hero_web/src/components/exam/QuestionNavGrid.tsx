import { useEffect, useMemo, useState } from 'react'
import { Button, Chip } from '@heroui/react'

interface QuestionNavGridProps {
  questionIds: string[]
  currentQuestionId?: string
  answeredIds: Set<string>
  markedIds: Set<string>
  onJump: (index: number) => void
}

const COLLAPSE_THRESHOLD = 60

function getNumberSizeClass(num: number): string {
  if (num >= 100) return 'question-nav-btn--3digit'
  if (num >= 10) return 'question-nav-btn--2digit'
  return 'question-nav-btn--1digit'
}

export function QuestionNavGrid({
  questionIds,
  currentQuestionId,
  answeredIds,
  markedIds,
  onJump,
}: QuestionNavGridProps) {
  const canCollapse = questionIds.length > COLLAPSE_THRESHOLD
  const [expanded, setExpanded] = useState(!canCollapse)

  useEffect(() => {
    setExpanded(!canCollapse)
  }, [canCollapse, questionIds.length])

  const useWideCells = questionIds.length >= 100
  const currentIndex = useMemo(
    () => questionIds.findIndex((id) => id === currentQuestionId),
    [questionIds, currentQuestionId],
  )

  return (
    <div>
      {canCollapse ? (
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-xs text-default-500">共 {questionIds.length} 题</span>
          <Button size="sm" variant="ghost" onPress={() => setExpanded((value) => !value)}>
            {expanded ? '收起' : '展开全部'}
          </Button>
        </div>
      ) : null}

      <div
        className={[
          `question-nav-grid${useWideCells ? ' question-nav-grid--wide' : ''}`,
          canCollapse && !expanded ? 'question-nav-grid--collapsed' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {questionIds.map((questionId, index) => {
          const num = index + 1
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
              className={`question-nav-btn ${getNumberSizeClass(num)}${
                isCurrent ? ' question-nav-btn--current' : ''
              }`}
              onPress={() => onJump(index)}
            >
              {num}
            </Button>
          )
        })}
      </div>

      {canCollapse && !expanded && currentIndex >= 0 ? (
        <p className="mt-2 text-xs text-default-500">
          当前第 {currentIndex + 1} 题，点击「展开全部」查看完整题号
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2 text-xs text-default-500">
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
