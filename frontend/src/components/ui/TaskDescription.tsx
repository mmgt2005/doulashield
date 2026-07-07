interface TaskDescriptionProps {
  text: string
  className?: string
}

/**
 * Renders a task description. If the text contains "Step N — Title:" patterns
 * (as found in MCO contracting tasks), each step is split onto its own line with
 * the header bolded. Plain descriptions without that pattern render as normal text.
 */
export default function TaskDescription({ text, className = '' }: TaskDescriptionProps) {
  const parts = text.split(/(?=Step \d+ —)/).filter(Boolean)
  const hasSteps = parts.length > 1 || /^Step \d+ —/.test(text)

  if (!hasSteps) {
    return <p className={`text-xs text-gray-500 leading-relaxed ${className}`}>{text}</p>
  }

  return (
    <div className={`space-y-1.5 ${className}`}>
      {parts.map((part, i) => {
        const match = part.match(/^(Step \d+ —[^:]+:)\s*([\s\S]*)$/)
        if (match) {
          return (
            <div key={i} className="text-xs leading-relaxed">
              <span className="font-semibold text-gray-700">{match[1]}</span>{' '}
              <span className="text-gray-500">{match[2].trim()}</span>
            </div>
          )
        }
        return (
          <p key={i} className="text-xs text-gray-500 leading-relaxed">{part.trim()}</p>
        )
      })}
    </div>
  )
}
