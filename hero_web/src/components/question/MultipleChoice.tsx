import { Checkbox, CheckboxGroup } from '@heroui/react'
import { RichContent } from '@/components/question/RichContent'
import type { QuestionOption } from '@/types/question'

interface MultipleChoiceProps {
  options: QuestionOption[]
  value: string[]
  disabled?: boolean
  onChange: (value: string[]) => void
}

export function MultipleChoice({ options, value, disabled, onChange }: MultipleChoiceProps) {
  return (
    <CheckboxGroup value={value} isDisabled={disabled} onChange={onChange}>
      {options.map((option) => (
        <Checkbox key={option.option_label} value={option.option_label}>
          <Checkbox.Control>
            <Checkbox.Indicator />
          </Checkbox.Control>
          <Checkbox.Content>
            <span className="mr-2 font-medium">{option.option_label}.</span>
            <RichContent content={option.option_content} />
          </Checkbox.Content>
        </Checkbox>
      ))}
    </CheckboxGroup>
  )
}
