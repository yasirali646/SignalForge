/** Prepare agent/pipeline markdown for display (strip tool noise, normalize breaks). */

const LC_BLOCK_RE =
  /\{'type':\s*'text'[^}]*\}|\{"type":\s*"text"[^}]*\}/g

export function sanitizeMarkdown(content: string): string {
  if (!content) return ''

  let text = content.trim()

  // LangChain / tool message artifacts sometimes land in stored briefs
  text = text.replace(LC_BLOCK_RE, '')
  text = text.replace(/\[\{'type':\s*'text'[\s\S]*?\}\]/g, '')

  // Ensure headings and lists break onto their own lines
  text = text.replace(/\s*(#{1,3}\s)/g, '\n\n$1')
  text = text.replace(/\s+(- \*\*)/g, '\n$1')
  text = text.replace(/\s+(- https?:\/\/)/g, '\n$1')

  return text.replace(/\n{3,}/g, '\n\n').trim()
}

export function looksLikeMarkdown(content: string): boolean {
  const t = content.trim()
  return (
    /^#{1,3}\s/m.test(t) ||
    /\*\*[^*]+\*\*/.test(t) ||
    /^- /m.test(t) ||
    /^\d+\. /m.test(t)
  )
}
