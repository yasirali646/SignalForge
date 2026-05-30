/** Legacy style object — kept so stale HMR bundles don’t throw ReferenceError. */
export const CHART_TOOLTIP_STYLE = {
  background: 'rgba(10, 10, 24, 0.97)',
  border: '1px solid rgba(34, 211, 238, 0.28)',
  borderRadius: '8px',
  color: '#f0f4ff',
  fontSize: '0.8rem',
} as const

export const CHART_TOOLTIP_ITEM_STYLE = {
  color: '#f0f4ff',
  background: 'transparent',
} as const

export const CHART_TOOLTIP_LABEL_STYLE = {
  color: '#8b92b3',
  marginBottom: '0.25rem',
} as const

type TooltipEntry = {
  name?: string
  value?: number | string
  color?: string
  dataKey?: string | number
  payload?: { fill?: string }
}

type ChartTooltipProps = {
  active?: boolean
  payload?: TooltipEntry[]
  label?: string | number
  valueSuffix?: string
}

export function ChartTooltip({
  active,
  payload,
  label,
  valueSuffix = '',
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null

  return (
    <div className="chart-tooltip">
      {label != null && label !== '' && (
        <p className="chart-tooltip-label">{String(label)}</p>
      )}
      <ul className="chart-tooltip-list">
        {payload.map((entry) => {
          const name = entry.name ?? entry.dataKey ?? 'Value'
          const value = entry.value ?? 0
          return (
            <li key={`${String(name)}-${String(entry.dataKey)}`}>
              <span
                className="chart-tooltip-swatch"
                style={{
                  background: entry.color ?? entry.payload?.fill ?? '#22d3ee',
                }}
              />
              <span className="chart-tooltip-text">
                {name}: {value}
                {valueSuffix}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export const CHART_CURSOR = {
  fill: 'rgba(34, 211, 238, 0.08)',
  stroke: 'rgba(34, 211, 238, 0.2)',
  strokeWidth: 1,
}
