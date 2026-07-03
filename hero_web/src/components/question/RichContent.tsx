import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

interface RichContentProps {
  content: string
  className?: string
  inline?: boolean
}

export function RichContent({ content, className = '', inline = false }: RichContentProps) {
  return (
    <div className={`prose-question${inline ? ' prose-question--inline' : ''} ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
