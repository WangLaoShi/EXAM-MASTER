import type {
  CompositeUserAnswer,
  LeafUserAnswer,
  PracticeQuestion,
  QuestionOption,
  QuestionType,
  UserAnswer,
} from '@/types/question'

export type SubQuestionType = Exclude<QuestionType, 'composite'>

export interface SubQuestion {
  id: string
  type: SubQuestionType
  stem: string
  options?: QuestionOption[]
  blank_count?: number
}

export function normalizeSubQuestions(metaData?: Record<string, unknown> | null): SubQuestion[] {
  const raw = metaData?.sub_questions
  if (!Array.isArray(raw)) return []

  return raw.map((item, index) => {
    const sub = item as Record<string, unknown>
    const options = Array.isArray(sub.options)
      ? sub.options.map((opt) => {
          const o = opt as Record<string, unknown>
          return {
            option_label: String(o.label ?? o.option_label ?? ''),
            option_content: String(o.content ?? o.option_content ?? ''),
          }
        })
      : undefined

    return {
      id: String(sub.id ?? sub.sub_id ?? index + 1),
      type: String(sub.type ?? 'single') as SubQuestionType,
      stem: String(sub.stem ?? ''),
      options,
      blank_count: typeof sub.blank_count === 'number' ? sub.blank_count : undefined,
    }
  })
}

function isSubAnswerFilled(type: SubQuestionType, answer: LeafUserAnswer | undefined): boolean {
  if (!answer) return false
  if (type === 'single' || type === 'essay') {
    return 'answer' in answer && String(answer.answer ?? '').trim().length > 0
  }
  if (type === 'multiple') {
    return 'answers' in answer && Array.isArray(answer.answers) && answer.answers.length > 0
  }
  if (type === 'judge') {
    return 'answer' in answer && typeof answer.answer === 'boolean'
  }
  if (type === 'fill') {
    return (
      'answers' in answer &&
      Array.isArray(answer.answers) &&
      answer.answers.some((item) => String(item ?? '').trim().length > 0)
    )
  }
  return false
}

export function isCompositeAnswerComplete(
  subQuestions: SubQuestion[],
  value: CompositeUserAnswer | null,
): boolean {
  if (!value?.sub_answers || subQuestions.length === 0) return false
  return subQuestions.every((sub) => isSubAnswerFilled(sub.type, value.sub_answers[sub.id]))
}

export function isAnswerComplete(question: PracticeQuestion, value: UserAnswer | null): boolean {
  if (!value) return false
  if (question.type === 'composite') {
    return isCompositeAnswerComplete(normalizeSubQuestions(question.meta_data), value as CompositeUserAnswer)
  }
  if (question.type === 'single' || question.type === 'essay') {
    return 'answer' in value && String(value.answer ?? '').trim().length > 0
  }
  if (question.type === 'multiple') {
    return 'answers' in value && Array.isArray(value.answers) && value.answers.length > 0
  }
  if (question.type === 'judge') {
    return 'answer' in value && typeof value.answer === 'boolean'
  }
  if (question.type === 'fill') {
    return 'answers' in value && Array.isArray(value.answers) && value.answers.some(Boolean)
  }
  return false
}

export function getSubTypeLabel(type: SubQuestionType): string {
  const labels: Record<SubQuestionType, string> = {
    single: '单选',
    multiple: '多选',
    judge: '判断',
    fill: '填空',
    essay: '简答',
  }
  return labels[type] ?? type
}
