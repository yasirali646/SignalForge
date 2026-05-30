import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Event } from '../types'
import {
  SEVERITY_COLORS,
  buildCompetitorSeries,
  buildDailySeries,
  buildSeveritySeries,
  buildTypeSeries,
} from '../utils/chartData'
import {
  CHART_CURSOR,
  CHART_TOOLTIP_ITEM_STYLE,
  CHART_TOOLTIP_LABEL_STYLE,
  ChartTooltip,
} from './ChartTooltip'

/** Re-export — fixes stale HMR referencing CHART_TOOLTIP_STYLE from this module */
export { CHART_TOOLTIP_STYLE } from './ChartTooltip'

interface OverviewChartsProps {
  events: Event[]
}

function ChartEmpty({ message }: { message: string }) {
  return <p className="chart-empty">{message}</p>
}

export function OverviewCharts({ events }: OverviewChartsProps) {
  const daily = buildDailySeries(events)
  const severity = buildSeveritySeries(events)
  const types = buildTypeSeries(events)
  const competitors = buildCompetitorSeries(events)
  const hasEvents = events.length > 0
  const severityTotal = severity.reduce((n, s) => n + s.value, 0)

  return (
    <section className="charts-section" aria-label="Intelligence charts">
      <div className="charts-grid">
        <article className="panel chart-panel">
          <header className="panel-header">Activity (14 days)</header>
          <div className="chart-body">
            {!hasEvents ? (
              <ChartEmpty message="No events yet — run Collect or simulate a change." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={daily} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: '#8b92b3', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fill: '#8b92b3', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={28}
                  />
                  <Tooltip
                    content={<ChartTooltip valueSuffix=" events" />}
                    cursor={CHART_CURSOR}
                    itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                    labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                    wrapperStyle={{ outline: 'none' }}
                    labelFormatter={(_, payload) =>
                      payload?.[0]?.payload?.date
                        ? new Date(String(payload[0].payload.date)).toLocaleDateString(
                            undefined,
                            { weekday: 'short', month: 'short', day: 'numeric' }
                          )
                        : ''
                    }
                  />
                  <Bar dataKey="count" fill="#22d3ee" radius={[4, 4, 0, 0]} maxBarSize={28} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </article>

        <article className="panel chart-panel">
          <header className="panel-header">By severity</header>
          <div className="chart-body chart-body--pie">
            {!hasEvents || severityTotal === 0 ? (
              <ChartEmpty message="Severity breakdown appears after events are detected." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severity.filter((s) => s.value > 0)}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={2}
                    stroke="none"
                  >
                    {severity
                      .filter((s) => s.value > 0)
                      .map((entry) => (
                        <Cell key={entry.severity} fill={entry.fill} />
                      ))}
                  </Pie>
                  <Tooltip
                    content={<ChartTooltip />}
                    itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                    labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                    wrapperStyle={{ outline: 'none' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
            {hasEvents && severityTotal > 0 && (
              <ul className="chart-legend chart-legend--inline">
                {severity.map((s) => (
                  <li key={s.severity}>
                    <span
                      className="chart-legend-swatch"
                      style={{ background: SEVERITY_COLORS[s.severity] }}
                    />
                    {s.name} ({s.value})
                  </li>
                ))}
              </ul>
            )}
          </div>
        </article>

        <article className="panel chart-panel">
          <header className="panel-header">Signal types</header>
          <div className="chart-body">
            {types.length === 0 ? (
              <ChartEmpty message="Signal mix shows pricing, messaging, hiring, and news events." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={types}
                  margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
                >
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={88}
                    tick={{ fill: '#8b92b3', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    content={<ChartTooltip valueSuffix=" events" />}
                    cursor={CHART_CURSOR}
                    itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                    labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                    wrapperStyle={{ outline: 'none' }}
                  />
                  <Bar dataKey="value" fill="#a78bfa" radius={[0, 4, 4, 0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </article>

        <article className="panel chart-panel">
          <header className="panel-header">Top competitors</header>
          <div className="chart-body">
            {competitors.length === 0 ? (
              <ChartEmpty message="Add competitors and collect data to compare activity." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={competitors}
                  margin={{ top: 8, right: 8, left: -12, bottom: 0 }}
                >
                  <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#8b92b3', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval={0}
                    angle={-18}
                    textAnchor="end"
                    height={52}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fill: '#8b92b3', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    width={28}
                  />
                  <Tooltip
                    content={<ChartTooltip valueSuffix=" events" />}
                    cursor={CHART_CURSOR}
                    itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                    labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                    wrapperStyle={{ outline: 'none' }}
                  />
                  <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={32} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </article>
      </div>
    </section>
  )
}
