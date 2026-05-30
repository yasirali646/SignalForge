import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { sanitizeMarkdown } from '../utils/markdown'

interface AgentMarkdownProps {
  content: string
  className?: string
}

export function AgentMarkdown({ content, className = '' }: AgentMarkdownProps) {
  const cleaned = sanitizeMarkdown(content)
  return (
    <div className={`agent-markdown ${className}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="md-table-wrap">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {cleaned}
      </ReactMarkdown>
    </div>
  )
}
