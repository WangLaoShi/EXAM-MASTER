import { Alert, Chip } from '@heroui/react'
import { EssayAnswer } from '@/components/question/EssayAnswer'
import { FillBlank } from '@/components/question/FillBlank'
import { JudgeChoice } from '@/components/question/JudgeChoice'
import { MultipleChoice } from '@/components/question/MultipleChoice'
import { RichContent } from '@/components/question/RichContent'
import { SingleChoice } from '@/components/question/SingleChoice'
import type { AnswerResult } from '@/types/practice'
import type { PracticeQuestion, UserAnswer } from '@/types/question'

interface QuestionRendererProps {
  question: PracticeQuestion
  value: UserAnswer | null
  disabled?: boolean
  result?: AnswerResult | null
  onChange: (value: UserAnswer) => void
}

function getTypeLabel(type: PracticeQuestion['type']): string {
  const labels: Record<PracticeQuestion['type'], string> = {
    single: '单选题',
    multiple: '多选题',
    judge: '判断题',
    fill: '填空题',
    essay: '简答题',
    composite: '复合题',
  }
  return labels[type] ?? type
}

export function QuestionRenderer({
  question,
  value,
  disabled,
  result,
  onChange,
}: QuestionRendererProps) {
  const options = (question.options ?? []).map((option) => ({
    option_label: option.option_label ?? (option as { label?: string }).label ?? '',
    option_content: option.option_content ?? (option as { content?: string }).content ?? '',
    is_correct: option.is_correct,
  }))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-2">
        <Chip size="sm" variant="soft">
          {getTypeLabel(question.type)}
        </Chip>
        {question.difficulty ? (
          <Chip size="sm" variant="secondary">
            {question.difficulty}
          </Chip>
        ) : null}
        {question.is_favorite ? (
          <Chip size="sm" color="warning" variant="soft">
            已收藏
          </Chip>
        ) : null}
        {question.is_wrong_before ? (
          <Chip size="sm" color="danger" variant="soft">
            曾做错
          </Chip>
        ) : null}
      </div>

      <RichContent content={question.stem} />

      <div>
        {question.type === 'single' ? (
          <SingleChoice
            options={options}
            disabled={disabled}
            value={(value as { answer?: string } | null)?.answer}
            onChange={(answer) => onChange({ answer })}
          />
        ) : null}

        {question.type === 'multiple' ? (
          <MultipleChoice
            options={options}
            disabled={disabled}
            value={(value as { answers?: string[] } | null)?.answers ?? []}
            onChange={(answers) => onChange({ answers })}
          />
        ) : null}

        {question.type === 'judge' ? (
          <JudgeChoice
            disabled={disabled}
            value={
              value && 'answer' in value ? String((value as { answer: unknown }).answer) : undefined
            }
            onChange={(answer) => onChange({ answer: answer === 'true' })}
          />
        ) : null}

        {question.type === 'fill' ? (
          <FillBlank
            count={Math.max(options.length, 1)}
            disabled={disabled}
            value={(value as { answers?: string[] } | null)?.answers ?? []}
            onChange={(answers) => onChange({ answers })}
          />
        ) : null}

        {question.type === 'essay' ? (
          <EssayAnswer
            disabled={disabled}
            value={(value as { answer?: string } | null)?.answer ?? ''}
            onChange={(answer) => onChange({ answer })}
          />
        ) : null}

        {question.type === 'composite' ? (
          <Alert status="warning">复合题暂未实现，请使用 Flutter 客户端或后续版本。</Alert>
        ) : null}
      </div>

      {result ? (
        <Alert status={result.is_correct ? 'success' : 'danger'}>
          <div className="flex flex-col gap-2">
            <strong>{result.is_correct ? '回答正确' : '回答错误'}</strong>
            {result.explanation ? <RichContent content={result.explanation} /> : null}
          </div>
        </Alert>
      ) : null}
    </div>
  )
}
