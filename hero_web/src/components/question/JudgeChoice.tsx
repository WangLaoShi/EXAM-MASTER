import { Radio, RadioGroup } from '@heroui/react'

interface JudgeChoiceProps {
  value?: string
  disabled?: boolean
  onChange: (value: string) => void
}

export function JudgeChoice({ value, disabled, onChange }: JudgeChoiceProps) {
  return (
    <RadioGroup value={value} isDisabled={disabled} onChange={onChange}>
      <Radio value="true">
        <Radio.Control>
          <Radio.Indicator />
        </Radio.Control>
        <Radio.Content>正确</Radio.Content>
      </Radio>
      <Radio value="false">
        <Radio.Control>
          <Radio.Indicator />
        </Radio.Control>
        <Radio.Content>错误</Radio.Content>
      </Radio>
    </RadioGroup>
  )
}
