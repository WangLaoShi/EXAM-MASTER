import { Input } from '@heroui/react'

interface FillBlankProps {
  count: number
  value: string[]
  disabled?: boolean
  onChange: (value: string[]) => void
}

export function FillBlank({ count, value, disabled, onChange }: FillBlankProps) {
  const blanks = Array.from({ length: Math.max(count, 1) }, (_, index) => value[index] ?? '')

  return (
    <div className="flex flex-col gap-3">
      {blanks.map((item, index) => (
        <div key={index} className="flex items-center gap-3">
          <span className="w-8 text-sm text-default-500">{index + 1}.</span>
          <Input
            fullWidth
            disabled={disabled}
            placeholder={`第 ${index + 1} 空`}
            value={item}
            onChange={(event) => {
              const next = [...blanks]
              next[index] = event.target.value
              onChange(next)
            }}
          />
        </div>
      ))}
    </div>
  )
}
