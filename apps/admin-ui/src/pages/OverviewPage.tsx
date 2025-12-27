import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Card,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Button,
  ThemeIcon,
  Title,
} from '@mantine/core'
import type { ReactNode } from 'react'
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Activity, Flame, Layers, Mic2 } from 'lucide-react'
import {
  api,
  type DiscoveryCoverageReport,
  type DiscoveryRun,
  type DiscoverySummary,
  type LanguageLabelMapRequest,
  type LanguageLabelMapRow,
  type LanguageTaxonomyRow,
  type PipelineErrorRow,
  type PipelineActivityResponse,
  type SummaryResponse,
  type UnmappedLanguageLabel,
} from '../lib/api'
import type { NavKey } from '../components/layout/SidebarNav'
import { formatDateTime, formatNumber } from '../lib/format'

type StatCardProps = {
  label: string
  value: string
  helper?: string
  icon: ReactNode
  onClick?: () => void
}

const StatCard = ({ label, value, helper, icon, onClick }: StatCardProps) => (
  <Card
    component="button"
    onClick={onClick}
    shadow="lg"
    radius="xl"
    withBorder
    style={{
      textAlign: 'left',
      transition: 'transform 120ms ease, box-shadow 120ms ease',
    }}
    onMouseEnter={(event) => {
      event.currentTarget.style.transform = 'translateY(-2px)'
    }}
    onMouseLeave={(event) => {
      event.currentTarget.style.transform = 'translateY(0)'
    }}
  >
    <Group justify="space-between" align="center">
      <Stack gap={4}>
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
          {label}
        </Text>
        <Title order={3}>{value}</Title>
        {helper ? (
          <Text size="xs" c="dimmed">
            {helper}
          </Text>
        ) : null}
      </Stack>
      <ThemeIcon size={44} radius="lg" variant="light" color="cyan">
        {icon}
      </ThemeIcon>
    </Group>
  </Card>
)

type OverviewPageProps = {
  onNavigate?: (view: NavKey) => void
}

export const OverviewPage = ({ onNavigate }: OverviewPageProps) => {
  const { data, isLoading, error, dataUpdatedAt } = useQuery<SummaryResponse>({
    queryKey: ['summary', 'today'],
    queryFn: api.getSummary,
    refetchInterval: 15_000,
  })
  const { data: pipelineActivity } = useQuery<PipelineActivityResponse>({
    queryKey: ['pipeline', 'activity'],
    queryFn: () => api.getPipelineActivity(),
    refetchInterval: 15_000,
  })
  const { data: discoverySummary } = useQuery<DiscoverySummary[]>({
    queryKey: ['discovery', 'summary'],
    queryFn: api.getDiscoverySummary,
    refetchInterval: 60_000,
  })
  const { data: discoveryCoverage } = useQuery<DiscoveryCoverageReport>({
    queryKey: ['discovery', 'coverage'],
    queryFn: api.getDiscoveryCoverage,
    refetchInterval: 60_000,
  })
  const refreshCoverage = useMutation({
    mutationFn: api.refreshDiscoveryCoverage,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['discovery', 'coverage'] })
    },
  })
  const { data: unmappedLabels } = useQuery<UnmappedLanguageLabel[]>({
    queryKey: ['language', 'unmapped'],
    queryFn: () => api.getUnmappedLanguageLabels(12),
    refetchInterval: 60_000,
  })
  const { data: taxonomy } = useQuery<LanguageTaxonomyRow[]>({
    queryKey: ['language', 'taxonomy'],
    queryFn: api.getLanguageTaxonomy,
    refetchInterval: 120_000,
  })
  const { data: labelMap } = useQuery<LanguageLabelMapRow[]>({
    queryKey: ['language', 'label-map'],
    queryFn: () => api.getLanguageLabelMap(200),
    refetchInterval: 120_000,
  })
  const queryClient = useQueryClient()
  const upsertLabelMap = useMutation({
    mutationFn: api.upsertLanguageLabelMap,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['language', 'unmapped'] })
      queryClient.invalidateQueries({ queryKey: ['language', 'label-map'] })
    },
  })
  const [labelNotes, setLabelNotes] = useState<Record<string, string>>({})
  const [labelSelection, setLabelSelection] = useState<Record<string, string | null>>({})
  const { data: pipelineErrors } = useQuery<PipelineErrorRow[]>({
    queryKey: ['pipeline', 'errors'],
    queryFn: () => api.getPipelineErrors(10, 24),
    refetchInterval: 60_000,
  })

  const taxonomyOptions = useMemo(
    () =>
      (taxonomy ?? []).map((row) => ({
        value: row.iso639_3,
        label: `${row.name} (${row.iso639_3})`,
      })),
    [taxonomy],
  )
  const { data: discoveryRuns } = useQuery<DiscoveryRun[]>({
    queryKey: ['discovery', 'runs'],
    queryFn: () => api.getDiscoveryRuns(3),
    refetchInterval: 30_000,
  })

  if (isLoading) {
    return <div className="text-sm text-slate-400">Loading summary…</div>
  }

  const renderEmptyState = (title: string, description: string) => (
    <Card shadow="lg" radius="xl" withBorder>
      <Stack gap="xs">
        <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
          {title}
        </Text>
        <Title order={4}>{description}</Title>
        <Stack gap={4} mt="sm">
          <Text size="sm" c="dimmed">
            1) Run `./scripts/local_radio_bootstrap.sh` to start Postgres + migrations.
          </Text>
          <Text size="sm" c="dimmed">
            2) Export `DATABASE_URL` and run station discovery.
          </Text>
          <Text size="sm" c="dimmed">
            3) Start the API: `./scripts/start_radio_ingestion_api.sh`.
          </Text>
        </Stack>
      </Stack>
    </Card>
  )

  if (error || !data) {
    return renderEmptyState('No data yet', 'Connect the ingestion API to see live summary.')
  }

  const isEmpty =
    data.counts.sources_active === 0 && data.counts.segments_created === 0

  if (isEmpty) {
    return renderEmptyState('Empty state', 'Run discovery + capture to populate stations.')
  }

  const freshnessLabel = dataUpdatedAt
    ? `Updated ${Math.round((Date.now() - dataUpdatedAt) / 1000)}s ago`
    : undefined

  return (
    <Stack gap="xl">
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <StatCard
          label="Active Sources"
          value={formatNumber(data.counts.sources_active)}
          helper="Stations + feeds"
          icon={<Activity className="h-5 w-5" />}
          onClick={() => onNavigate?.('sources')}
        />
        <StatCard
          label="Hours Recorded"
          value={formatNumber(data.counts.hours_recorded, 1)}
          helper="Last 24h"
          icon={<Mic2 className="h-5 w-5" />}
          onClick={() => onNavigate?.('sources')}
        />
        <StatCard
          label="Speech Kept"
          value={formatNumber(data.counts.speech_hours, 1)}
          helper="Speech-only time"
          icon={<Flame className="h-5 w-5" />}
          onClick={() => onNavigate?.('sources')}
        />
        <StatCard
          label="Segments Created"
          value={formatNumber(data.counts.segments_created)}
          helper={freshnessLabel}
          icon={<Layers className="h-5 w-5" />}
          onClick={() => onNavigate?.('segments')}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
        <Card shadow="lg" radius="xl" withBorder>
          <Group justify="space-between" align="center" mb="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
                Pipeline Flow
              </Text>
              <Title order={4}>Capture → Speech → Segments</Title>
            </Stack>
            <Text size="xs" c="dimmed">
              24h window
            </Text>
          </Group>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.timeseries} margin={{ left: -8, right: 16 }}>
                <defs>
                  <linearGradient id="capture" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#0f172a" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="speech" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0f172a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="ts"
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  tickFormatter={(value: string | number) =>
                    new Date(value).getHours().toString().padStart(2, '0')
                  }
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '12px',
                  }}
                  labelFormatter={(value: string | number) => new Date(value).toLocaleString()}
                />
                <Area
                  type="monotone"
                  dataKey="captured_minutes"
                  stroke="#22d3ee"
                  fill="url(#capture)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="speech_minutes"
                  stroke="#38bdf8"
                  fill="url(#speech)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card shadow="lg" radius="xl" withBorder>
          <Group justify="space-between" align="center" mb="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
                Discovery
              </Text>
              <Title order={4}>Directory coverage</Title>
            </Stack>
            <Text size="xs" c="dimmed">
              Live
            </Text>
          </Group>
          <Stack gap={8}>
            {(discoverySummary ?? []).length > 0 ? (
              discoverySummary?.slice(0, 4).map((row) => (
                <Group key={row.source_name} justify="space-between" align="center">
                  <Text size="sm" fw={600}>
                    {row.source_name}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {formatNumber(row.total_discovered)} found
                  </Text>
                </Group>
              ))
            ) : (
              <Text size="sm" c="dimmed">
                No discovery summary yet.
              </Text>
            )}
            <Stack gap={4} mt="sm">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 1.5 }}>
                Latest runs
              </Text>
              {(discoveryRuns ?? []).map((run) => (
                <Group key={run.id} justify="space-between" align="center">
                  <Text size="xs" c="dimmed">
                    {run.source_name} {run.country ? `· ${run.country}` : ''}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {run.status} · {run.stats?.discovered ?? 0}
                  </Text>
                </Group>
              ))}
            </Stack>
          </Stack>
        </Card>

        <Card shadow="lg" radius="xl" withBorder>
          <Group justify="space-between" align="center" mb="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
                Coverage
              </Text>
              <Title order={4}>Country totals</Title>
            </Stack>
            <Group gap="sm">
              <Text size="xs" c="dimmed">
                {discoveryCoverage?.generated_at
                  ? formatDateTime(discoveryCoverage.generated_at)
                  : 'No report'}
              </Text>
              <Button
                size="xs"
                variant="light"
                loading={refreshCoverage.isPending}
                onClick={() => refreshCoverage.mutate()}
              >
                Refresh
              </Button>
            </Group>
          </Group>
          <Stack gap={8}>
            {(discoveryCoverage?.countries ?? []).length > 0 ? (
              discoveryCoverage?.countries.map((country) => (
                <Stack key={country.country ?? 'unknown'} gap={4}>
                  <Group justify="space-between">
                    <Text size="sm" fw={600}>
                      {country.country ?? 'Unknown'}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {formatNumber(country.canonical_station_count)} unique
                    </Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="xs" c="dimmed">
                      {formatNumber(country.total_discovered)} discovered ·{' '}
                      {formatNumber(country.total_inserted)} inserted
                    </Text>
                    <Text size="xs" c="dimmed">
                      {formatNumber(country.provenance_count)} source rows ·{' '}
                      {country.sources.length} directories
                    </Text>
                  </Group>
                  {country.audio_quality ? (
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">
                        {country.audio_quality.avg_bitrate_kbps !== null
                          ? `${formatNumber(country.audio_quality.avg_bitrate_kbps, 1)} kbps`
                          : 'Bitrate n/a'}{' '}
                        ·{' '}
                        {country.audio_quality.bitrate_stddev_kbps !== null
                          ? `±${formatNumber(country.audio_quality.bitrate_stddev_kbps, 1)}`
                          : 'σ n/a'}
                      </Text>
                      <Text size="xs" c="dimmed">
                        Dropouts {formatNumber(country.audio_quality.dropout_count)} · Silence{' '}
                        {country.audio_quality.avg_silence_ratio !== null
                          ? `${formatNumber(country.audio_quality.avg_silence_ratio * 100, 1)}%`
                          : 'n/a'}
                      </Text>
                    </Group>
                  ) : null}
                  {country.language_mapping ? (
                    <Group justify="space-between">
                      <Text size="xs" c="dimmed">
                        Mapped {formatNumber(country.language_mapping.mapped_segments)} /{' '}
                        {formatNumber(country.language_mapping.total_segments)}
                      </Text>
                      <Text size="xs" c="dimmed">
                        Unmapped {formatNumber(country.language_mapping.unmapped_segments)}
                      </Text>
                    </Group>
                  ) : null}
                </Stack>
              ))
            ) : (
              <Text size="sm" c="dimmed">
                No coverage report yet.
              </Text>
            )}
          </Stack>
        </Card>

        <Card shadow="lg" radius="xl" withBorder>
          <Group justify="space-between" align="center" mb="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
                Language mapping
              </Text>
              <Title order={4}>Unmapped labels</Title>
            </Stack>
            <Text size="xs" c="dimmed">
              Last hour
            </Text>
          </Group>
          <Stack gap={8}>
            {(unmappedLabels ?? []).length > 0 ? (
              unmappedLabels?.map((item) => (
                <Stack key={item.label} gap={6}>
                  <Group justify="space-between">
                    <Text size="sm" fw={600}>
                      {item.label}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {formatNumber(item.count)}
                    </Text>
                  </Group>
                  <Group align="flex-end" grow>
                    <Select
                      label="Canonical ISO-639-3"
                      placeholder="Select language"
                      data={taxonomyOptions}
                      searchable
                      nothingFoundMessage="No matches"
                      value={
                        labelSelection[item.label] ??
                        labelMap?.find((row) => row.observed_label === item.label)
                          ?.canonical_iso639_3 ??
                        null
                      }
                      onChange={(value) =>
                        setLabelSelection((prev) => ({ ...prev, [item.label]: value }))
                      }
                    />
                    <TextInput
                      label="Notes"
                      placeholder="Optional notes"
                      value={labelNotes[item.label] ?? ''}
                      onChange={(event) =>
                        setLabelNotes((prev) => ({
                          ...prev,
                          [item.label]: event.currentTarget.value,
                        }))
                      }
                    />
                    <Button
                      variant="light"
                      onClick={() => {
                        const payload: LanguageLabelMapRequest = {
                          observed_label: item.label,
                          canonical_iso639_3: labelSelection[item.label] ?? null,
                          source: 'admin',
                          notes: labelNotes[item.label] ?? null,
                        }
                        upsertLabelMap.mutate(payload)
                      }}
                    >
                      Save
                    </Button>
                  </Group>
                </Stack>
              ))
            ) : (
              <Text size="sm" c="dimmed">
                No unmapped labels detected.
              </Text>
            )}
          </Stack>
        </Card>

        <Card shadow="lg" radius="xl" withBorder>
          <Stack gap="xs">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Top Languages
            </Text>
            <Title order={4}>By minutes today</Title>
          </Stack>
          <Stack gap="sm" mt="md">
            {data.top_languages.map((lang: SummaryResponse['top_languages'][number]) => (
              <Card key={lang.lang} radius="lg" withBorder>
                <Group justify="space-between">
                  <Stack gap={2}>
                    <Text fw={600}>{lang.lang}</Text>
                    <Text size="xs" c="dimmed">
                      {formatNumber(lang.segments)} segments
                    </Text>
                  </Stack>
                  <Text c="cyan.3" fw={600}>
                    {formatNumber(lang.minutes, 1)} min
                  </Text>
                </Group>
              </Card>
            ))}
          </Stack>
        </Card>
      </SimpleGrid>

      <Card shadow="lg" radius="xl" withBorder>
        <Group justify="space-between" align="flex-start">
          <Stack gap={2}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Error Radar
            </Text>
            <Title order={4}>Recent failures</Title>
          </Stack>
          <Text size="xs" c="dimmed">
            Last 24h
          </Text>
        </Group>
        <Stack gap="sm" mt="md">
          {(pipelineErrors ?? []).length > 0 ? (
            pipelineErrors?.map((row) => (
              <Card key={`${row.created_at}-${row.event_type}`} radius="lg" withBorder>
                <Stack gap={4}>
                  <Group justify="space-between">
                    <Text fw={600}>{row.event_type}</Text>
                    <Text size="xs" c="dimmed">
                      {formatDateTime(row.created_at)}
                    </Text>
                  </Group>
                  <Text size="sm" c="dimmed">
                    {row.stage} · {row.status}
                    {row.station_name ? ` · ${row.station_name}` : ''}
                  </Text>
                  {row.error_kind || row.error_detail ? (
                    <Text size="sm" c="red.3">
                      {row.error_kind ?? 'error'} — {row.error_detail ?? row.message ?? 'No detail'}
                    </Text>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {row.message ?? 'No detail'}
                    </Text>
                  )}
                </Stack>
              </Card>
            ))
          ) : (
            <Text size="sm" c="dimmed">
              No recent pipeline errors.
            </Text>
          )}
        </Stack>
      </Card>

      <Card shadow="lg" radius="xl" withBorder>
        <Group justify="space-between" align="flex-start">
          <Stack gap={2}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Verification Pulse
            </Text>
            <Title order={4}>LLM language checks</Title>
          </Stack>
          <Stack gap={2} align="flex-end">
            <Text size="xs" c="dimmed">
              Last {data.window_hours}h
            </Text>
            <Title order={3}>{formatNumber(data.verification_summary.total)}</Title>
          </Stack>
        </Group>
        {data.verification_summary.total === 0 ? (
          <Text size="sm" c="dimmed" mt="md">
            No verification runs yet. Trigger audio-lane or radio exports to populate.
          </Text>
        ) : (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm" mt="md">
            {data.verification_summary.top_languages.map((lang) => (
              <Card key={lang.lang} radius="lg" withBorder>
                <Group justify="space-between">
                  <Text fw={600}>{lang.lang}</Text>
                  <Text c="cyan.3" fw={600}>
                    {formatNumber(lang.count)}
                  </Text>
                </Group>
              </Card>
            ))}
          </SimpleGrid>
        )}
      </Card>

      <Card shadow="lg" radius="xl" withBorder>
        <Group justify="space-between" align="flex-start">
          <Stack gap={2}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Pipeline Activity
            </Text>
            <Title order={4}>Last seen by stage</Title>
          </Stack>
          <Text size="xs" c="dimmed">
            Live view
          </Text>
        </Group>
        {pipelineActivity && pipelineActivity.stages.length > 0 ? (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm" mt="md">
            {pipelineActivity.stages.map((stage) => (
              <Card key={stage.stage} radius="lg" withBorder>
                <Stack gap={2}>
                  <Group justify="space-between">
                    <Text fw={600}>{stage.stage}</Text>
                    <Text c="cyan.3" fw={600}>
                      {formatNumber(stage.total_count)}
                    </Text>
                  </Group>
                  <Text size="xs" c="dimmed">
                    last seen {stage.last_seen ? formatDateTime(stage.last_seen) : '—'}
                  </Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        ) : (
          <Text size="sm" c="dimmed" mt="md">
            No pipeline events recorded yet.
          </Text>
        )}
      </Card>

      <Card shadow="lg" radius="xl" withBorder>
        <Group justify="space-between" align="flex-start">
          <Stack gap={2}>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Capture Health
            </Text>
            <Title order={4}>Recent station captures</Title>
          </Stack>
          <Text size="xs" c="dimmed">
            {pipelineActivity?.window_hours ?? 24}h window
          </Text>
        </Group>
        {pipelineActivity?.capture_health ? (
          <Stack gap="sm" mt="md">
            <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm">
              <Card radius="lg" withBorder>
                <Text size="xs" c="dimmed">
                  Captures
                </Text>
                <Title order={4}>{formatNumber(pipelineActivity.capture_health.captures)}</Title>
              </Card>
              <Card radius="lg" withBorder>
                <Text size="xs" c="dimmed">
                  Failures
                </Text>
                <Title order={4} c="red.4">
                  {formatNumber(pipelineActivity.capture_health.failures)}
                </Title>
              </Card>
              <Card radius="lg" withBorder>
                <Text size="xs" c="dimmed">
                  Shards
                </Text>
                <Title order={4}>{formatNumber(pipelineActivity.capture_health.shard_count)}</Title>
              </Card>
              <Card radius="lg" withBorder>
                <Text size="xs" c="dimmed">
                  Stations
                </Text>
                <Title order={4}>{formatNumber(pipelineActivity.capture_health.station_count)}</Title>
              </Card>
            </SimpleGrid>
            <Stack gap={6}>
              {pipelineActivity.capture_health.recent_shards.map((shard) => (
                <Card key={shard.id} radius="lg" withBorder>
                  <Group justify="space-between">
                    <Stack gap={2}>
                      <Text fw={600}>{shard.station_name}</Text>
                      <Text size="xs" c="dimmed">
                        {shard.start_ts ? formatDateTime(shard.start_ts) : '—'} ·{' '}
                        {formatNumber(shard.duration, 0)}s
                      </Text>
                    </Stack>
                    <Text size="xs" c="dimmed">
                      {shard.capture_status ?? 'unknown'}
                    </Text>
                  </Group>
                </Card>
              ))}
            </Stack>
          </Stack>
        ) : (
          <Text size="sm" c="dimmed" mt="md">
            Capture health data is unavailable.
          </Text>
        )}
      </Card>

      <Card shadow="lg" radius="xl" withBorder>
        <Stack gap="xs">
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
            Error Radar
          </Text>
          <Title order={4}>Stage degradation</Title>
        </Stack>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm" mt="md">
          {data.errors_by_stage.map((stage: SummaryResponse['errors_by_stage'][number]) => (
            <Card key={stage.stage} radius="lg" withBorder>
              <Group justify="space-between">
                <Text size="sm">{stage.stage}</Text>
                <Text c="red.4" fw={600}>
                  {formatNumber(stage.count)}
                </Text>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      </Card>
    </Stack>
  )
}
