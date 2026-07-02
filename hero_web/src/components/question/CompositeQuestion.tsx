import { Card, Chip } from '@heroui/react'
import { EssayAnswer } from '@/components/question/EssayAnswer'
import { FillBlank } from '@/components/question/FillBlank'
import { JudgeChoice } from '@/components/question/JudgeChoice'
import { MultipleChoice } from '@/components/question/MultipleChoice'
import { RichContent } from '@/components/question/RichContent'
import { SingleChoice } from '@/components/question/SingleChoice'
import type { CompositeUserAnswer, LeafUserAnswer, PracticeQuestion } from '@/types/question'
import { getSubTypeLabel, normalizeSubQuestions } from '@/utils/compositeQuestion'

interface CompositeQuestionProps {
  question: PracticeQuestion
  value: CompositeUserAnswer | null
  disabled?: boolean
  onChange: (value: CompositeUserAnswer) => void
}

export function CompositeQuestion({ question, value, disabled, onChange }: CompositeQuestionProps) {
  const subQuestions = normalizeSubQuestions(question.meta_data)
  const subAnswers = value?.sub_answers ?? {}

  if (subQuestions.length === 0) {
    return (
      <Card className="border border-default-200 p-4">
        <p className="text-default-500">该复合题未配置子题（meta_data.sub_questions 为空）。</p>
      </Card>
    )
  }

  const updateSubAnswer = (subId: string, answer: LeafUserAnswer) => {
    onChange({
      sub_answers: {
        ...subAnswers,
        [subId]: answer,
      },
    })
  }

  return (
    <div className="flex flex-col gap-4">
      {subQuestions.map((sub, index) => {
        const subValue = subAnswers[sub.id]
        const options = sub.options ?? []
        const fillCount = sub.blank_count ?? Math.max(options.length, 1)

        return (
          <Card key={sub.id} className="border border-default-200 p-4">
            <Card.Header className="flex flex-row flex-wrap items-center gap-2 pb-3">
              <Chip size="sm" variant="soft">
                第 {index + 1} 小题
              </Chip>
              <Chip size="sm" variant="secondary">
                {getSubTypeLabel(sub.type)}
              </Chip>
            </Card.Header>
            <Card.Content className="flex flex-col gap-4">
              <RichContent content={sub.stem} />

              {sub.type === 'single' ? (
                <SingleChoice
                  options={options}
                  disabled={disabled}
                  value={(subValue as { answer?: string } | undefined)?.answer}
                  onChange={(answer) => updateSubAnswer(sub.id, { answer })}
                />
              ) : null}

              {sub.type === 'multiple' ? (
                <MultipleChoice
                  options={options}
                  disabled={disabled}
                  value={(subValue as { answers?: string[] } | undefined)?.answers ?? []}
                  onChange={(answers) => updateSubAnswer(sub.id, { answers })}
                />
              ) : null}

              {sub.type === 'judge' ? (
                <JudgeChoice
                  disabled={disabled}
                  value={
                    subValue && 'answer' in subValue
                      ? String((subValue as { answer: unknown }).answer)
                      : undefined
                  }
                  onChange={(answer) => updateSubAnswer(sub.id, { answer: answer === 'true' })}
                />
              ) : null}

              {sub.type === 'fill' ? (
                <FillBlank
                  count={fillCount}
                  disabled={disabled}
                  value={(subValue as { answers?: string[] } | undefined)?.answers ?? []}
                  onChange={(answers) => updateSubAnswer(sub.id, { answers })}
                />
              ) : null}

              {sub.type === 'essay' ? (
                <EssayAnswer
                  disabled={disabled}
                  value={(subValue as { answer?: string } | undefined)?.answer ?? ''}
                  onChange={(answer) => updateSubAnswer(sub.id, { answer })}
                />
              ) : null}
            </Card.Content>
          </Card>
        )
      })}
    </div>
  )
}
