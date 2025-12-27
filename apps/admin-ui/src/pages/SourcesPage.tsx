import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Card,
  Button,
  Group,
  ScrollArea,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import {
  Bar,
  BarChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Radio, SignalHigh, Waves } from 'lucide-react'
import {
  api,
  type CaptureTargets,
  type DiscoveryRun,
  type DiscoverySummary,
  type StationHourly,
  type StationSummary,
} from '../lib/api'
import { formatDateTime, formatNumber, formatPercent, formatHour } from '../lib/format'
import { StationDrawer } from '../components/sources/StationDrawer'

const buildLanguageSet = (rows: StationHourly[]) => {
  const langTotals = new Map<string, number>()
  rows.forEach((row) => {
    Object.entries(row.lang_mix || {}).forEach(([lang, value]) => {
      langTotals.set(lang, (langTotals.get(lang) ?? 0) + value)
    })
  })
  return Array.from(langTotals.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([lang]) => lang)
}

const buildChartData = (rows: StationHourly[], languages: string[]) =>
  rows.map((row) => {
    const bucket: Record<string, number | string> = {
      hour: formatHour(row.hour),
      switch_rate: row.switch_rate ?? 0,
    }
    languages.forEach((lang) => {
      bucket[lang] = row.lang_mix?.[lang] ?? 0
    })
    return bucket
  })

const LanguageBadge = ({ lang }: { lang: string }) => (
  <Text size="xs" c="dimmed" fw={600}>
    {lang}
  </Text>
)

const getHealthTone = (status?: string | null) => {
  switch (status) {
    case 'healthy':
      return { label: 'healthy', className: 'text-emerald-300' }
    case 'degraded':
      return { label: 'degraded', className: 'text-amber-300' }
    case 'down':
      return { label: 'down', className: 'text-rose-300' }
    default:
      return { label: 'unknown', className: 'text-slate-400' }
  }
}

type StationGroup = {
  key: string
  name: string
  country: string | null
  lang_hint: string | null
  entries: StationSummary[]
}

const groupStations = (stations: StationSummary[]): StationGroup[] => {
  const groups = new Map<string, StationGroup>()
  stations.forEach((station) => {
    const key = `${station.name}|${station.country ?? ''}|${station.lang_hint ?? ''}`
    const existing = groups.get(key)
    if (existing) {
      existing.entries.push(station)
    } else {
      groups.set(key, {
        key,
        name: station.name,
        country: station.country,
        lang_hint: station.lang_hint,
        entries: [station],
      })
    }
  })
  return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name))
}

const StationRow = ({
  group,
  isActive,
  onSelect,
}: {
  group: StationGroup
  isActive: boolean
  onSelect: (group: StationGroup) => void
}) => (
  <button
    className={`flex w-full flex-col gap-2 rounded-xl border p-3 text-left transition ${
      isActive
        ? 'border-cyan-500/60 bg-cyan-500/10 shadow-[0_10px_20px_rgba(34,211,238,0.1)]'
        : 'border-slate-800 bg-slate-950/60 hover:-translate-y-0.5 hover:border-slate-700 hover:bg-slate-950/80'
    }`}
    onClick={() => onSelect(group)}
    type="button"
  >
    <div className="flex items-center justify-between">
      <div>
        <div className="text-sm font-semibold text-slate-100">{group.name}</div>
        <div className="text-xs text-slate-500">
          {group.country ?? '—'} · {group.lang_hint ?? 'no hint'}
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <SignalHigh className="h-4 w-4" />
        <span className={getHealthTone(group.entries[0]?.health_status).className}>
          {getHealthTone(group.entries[0]?.health_status).label}
        </span>
      </div>
    </div>
    <div className="flex items-center justify-between text-xs text-slate-400">
      <span>Speech ratio</span>
      <span className="text-cyan-200">
        {group.entries[0]?.speech_ratio !== null && group.entries[0]?.speech_ratio !== undefined
          ? formatPercent(group.entries[0]?.speech_ratio ?? 0, 1)
          : '—'}
      </span>
    </div>
    <div className="flex flex-wrap gap-2">
      {group.entries[0]?.primary_lang ? (
        <LanguageBadge lang={group.entries[0].primary_lang ?? ''} />
      ) : null}
      {group.entries[0]?.lang_mix
        ? Object.keys(group.entries[0].lang_mix ?? {})
            .slice(0, 2)
            .map((lang) => <LanguageBadge key={lang} lang={lang} />)
        : null}
      {group.entries.length > 1 ? (
        <Text size="xs" c="cyan.3" fw={600}>
          {group.entries.length} streams
        </Text>
      ) : null}
      {group.entries[0]?.health_consecutive_failures ? (
        <Text size="xs" c="red.3" fw={600}>
          {group.entries[0]?.health_consecutive_failures} failures
        </Text>
      ) : null}
    </div>
  </button>
)

export const SourcesPage = () => {
  const [selectedStation, setSelectedStation] = useState<StationGroup | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [countryInput, setCountryInput] = useState('')
  const [languageInput, setLanguageInput] = useState('')
  const [healthFilter, setHealthFilter] = useState('all')
  const queryClient = useQueryClient()
  const { data: captureTargets } = useQuery<CaptureTargets>({
    queryKey: ['capture-targets'],
    queryFn: api.getCaptureTargets,
  })
  const updateTargets = useMutation({
    mutationFn: api.updateCaptureTargets,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['capture-targets'] }),
  })
  const { data: stations, isLoading } = useQuery<StationSummary[]>({
    queryKey: ['stations'],
    queryFn: api.getStations,
    refetchInterval: 30_000,
  })
  const {
    data: discoveryRuns,
    refetch: refetchDiscoveryRuns,
    isFetching: isFetchingDiscoveryRuns,
  } = useQuery<DiscoveryRun[]>({
    queryKey: ['discovery', 'runs'],
    queryFn: () => api.getDiscoveryRuns(12),
    refetchInterval: 30_000,
  })
  const {
    data: discoverySummary,
    refetch: refetchDiscoverySummary,
    isFetching: isFetchingDiscoverySummary,
  } = useQuery<DiscoverySummary[]>({
    queryKey: ['discovery', 'summary'],
    queryFn: api.getDiscoverySummary,
    refetchInterval: 60_000,
  })

  const { data: stationHours } = useQuery<{
    station_id: number
    hours: number
    rows: StationHourly[]
  }>({
    queryKey: ['station-hours', selectedStation?.entries[0]?.id],
    queryFn: () => api.getStationHours(selectedStation?.entries[0]?.id ?? 0, 24),
    enabled: Boolean(selectedStation?.entries[0]?.id),
  })

  const { languages, chartData } = useMemo(() => {
    const rows = stationHours?.rows ?? []
    const languageList = buildLanguageSet(rows)
    return {
      languages: languageList,
      chartData: buildChartData(rows, languageList),
    }
  }, [stationHours])

  const stationGroups = useMemo(
    () => {
      const grouped = stations ? groupStations(stations) : []
      if (healthFilter === 'all') return grouped
      return grouped.filter((group) => group.entries[0]?.health_status === healthFilter)
    },
    [stations, healthFilter],
  )
  const activeGroup = selectedStation ?? stationGroups?.[0] ?? null
  const activeStation = activeGroup?.entries[0] ?? null

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
      <Stack gap="md">
        <Card shadow="lg" radius="xl" withBorder>
          <Group gap="sm" align="center">
            <Radio className="h-4 w-4" />
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Sources
            </Text>
          </Group>
          <Title order={4} mt="sm">
            Stations & feeds
          </Title>
          <Text size="sm" c="dimmed">
            Review uptime, speech yield, and language mix per station.
          </Text>
          <Group gap="xs" mt="sm">
            <Badge color="green" variant="light">
              healthy
            </Badge>
            <Badge color="yellow" variant="light">
              degraded
            </Badge>
            <Badge color="red" variant="light">
              down
            </Badge>
            <Badge color="gray" variant="outline">
              unknown
            </Badge>
          </Group>
        </Card>
        <Card shadow="lg" radius="xl" withBorder>
          <Stack gap="sm">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Capture targets
            </Text>
            <Text size="sm" c="dimmed">
              Countries use ISO-3166-1 (GH, SO). Languages use ISO-639-3 (aka, som).
            </Text>
            <TextInput
              label="Countries"
              placeholder="GH, SO"
              value={countryInput}
              onChange={(event) => setCountryInput(event.currentTarget.value)}
              description={
                captureTargets?.countries?.length
                  ? `Current: ${captureTargets.countries.join(', ')}`
                  : 'No active targets'
              }
            />
            <TextInput
              label="Languages"
              placeholder="aka, som"
              value={languageInput}
              onChange={(event) => setLanguageInput(event.currentTarget.value)}
              description={
                captureTargets?.languages?.length
                  ? `Current: ${captureTargets.languages.join(', ')}`
                  : 'No language filter'
              }
            />
            <Group justify="flex-end">
              <Button
                variant="light"
                onClick={() => {
                  const countries = countryInput
                    .split(',')
                    .map((value) => value.trim())
                    .filter(Boolean)
                  const languages = languageInput
                    .split(',')
                    .map((value) => value.trim())
                    .filter(Boolean)
                  updateTargets.mutate({
                    countries,
                    languages,
                    active: true,
                  })
                }}
              >
                Save targets
              </Button>
            </Group>
          </Stack>
        </Card>
        <Card shadow="lg" radius="xl" withBorder>
          <Stack gap="sm">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Health filter
            </Text>
            <SegmentedControl
              value={healthFilter}
              onChange={setHealthFilter}
              data={[
                { label: 'All', value: 'all' },
                { label: 'Healthy', value: 'healthy' },
                { label: 'Degraded', value: 'degraded' },
                { label: 'Down', value: 'down' },
              ]}
            />
            <Text size="xs" c="dimmed">
              Showing {stationGroups.length} station groups
            </Text>
          </Stack>
        </Card>
        <Card shadow="lg" radius="xl" withBorder>
          <Stack gap="sm">
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Discovery activity
            </Text>
            <Group justify="space-between" align="center">
              <Text size="sm" c="dimmed">
                Latest runs and aggregate coverage
              </Text>
              <Button
                size="xs"
                variant="light"
                loading={isFetchingDiscoveryRuns || isFetchingDiscoverySummary}
                onClick={() => {
                  refetchDiscoveryRuns()
                  refetchDiscoverySummary()
                }}
              >
                Refresh
              </Button>
            </Group>
            <Stack gap={6}>
              {(discoverySummary ?? []).length > 0 ? (
                discoverySummary?.map((row) => (
                  <Group key={row.source_name} justify="space-between" align="center">
                    <div>
                      <Text size="sm" fw={600}>
                        {row.source_name}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {row.source_type} · {row.runs} runs
                      </Text>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <Text size="sm" fw={600}>
                        {formatNumber(row.total_discovered)} found
                      </Text>
                      <Text size="xs" c="dimmed">
                        {row.last_finished ? formatDateTime(row.last_finished) : '—'}
                      </Text>
                    </div>
                  </Group>
                ))
              ) : (
                <Text size="sm" c="dimmed">
                  No discovery runs yet.
                </Text>
              )}
            </Stack>
            <Stack gap={6} mt="sm">
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 1.5 }}>
                Recent runs
              </Text>
              {(discoveryRuns ?? []).map((run) => (
                <Group key={run.id} justify="space-between" align="center">
                  <div>
                    <Text size="sm" fw={600}>
                      {run.source_name} {run.country ? `· ${run.country}` : ''}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {run.status} · {run.stats?.discovered ?? 0} discovered
                      {run.error_message ? ` · ${run.error_message}` : ''}
                    </Text>
                  </div>
                  <Text size="xs" c="dimmed">
                    {run.finished_at ? formatDateTime(run.finished_at) : 'in progress'}
                  </Text>
                </Group>
              ))}
            </Stack>
          </Stack>
        </Card>
        <Card shadow="lg" radius="xl" withBorder>
          <ScrollArea h={520} offsetScrollbars>
            <Stack gap="sm">
              {isLoading ? (
                <Text size="sm" c="dimmed">
                  Loading stations…
                </Text>
              ) : stationGroups.length > 0 ? (
                stationGroups.map((group) => (
                  <StationRow
                    key={group.key}
                    group={group}
                    isActive={activeGroup?.key === group.key}
                    onSelect={(next) => {
                      setSelectedStation(next)
                      setDrawerOpen(true)
                    }}
                  />
                ))
              ) : (
                <Text size="sm" c="dimmed">
                  No stations yet. Run discovery with Ghana/Somalia config.
                </Text>
              )}
            </Stack>
          </ScrollArea>
        </Card>
      </Stack>

      <Stack gap="md">
        <Card shadow="lg" radius="xl" withBorder>
          <Group justify="space-between" align="center">
            <Stack gap={4}>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
                Station fingerprint
              </Text>
              <Title order={4}>{activeGroup?.name ?? 'Select a station'}</Title>
              <Text size="sm" c="dimmed">
                {activeStation?.last_successful_capture
                  ? `Last capture ${formatDateTime(activeStation.last_successful_capture)}`
                  : 'No recent capture'}
              </Text>
            </Stack>
            <Group gap="xs" align="center">
              <Waves className="h-4 w-4" />
              <Text size="xs" c="dimmed">
                {languages.join(' · ') || 'No language mix yet'}
              </Text>
            </Group>
          </Group>
          <div style={{ height: 300, marginTop: 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ left: -16, right: 16 }}>
                <XAxis dataKey="hour" tick={{ fill: '#64748b', fontSize: 12 }} />
                <YAxis tick={{ fill: '#64748b', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: '12px',
                  }}
                />
                {languages.map((lang, index) => (
                  <Bar
                    key={lang}
                    dataKey={lang}
                    stackId="lang"
                    fill={index % 2 === 0 ? '#22d3ee' : '#38bdf8'}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
                <Line
                  type="monotone"
                  dataKey="switch_rate"
                  stroke="#f97316"
                  strokeWidth={2}
                  dot={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          <Card shadow="lg" radius="xl" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Primary language
            </Text>
            <Title order={4} mt="xs">
              {activeStation?.primary_lang ?? '—'}
            </Title>
          </Card>
          <Card shadow="lg" radius="xl" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Speech ratio
            </Text>
            <Title order={4} mt="xs">
              {activeStation?.speech_ratio !== null && activeStation?.speech_ratio !== undefined
                ? formatPercent(activeStation.speech_ratio, 1)
                : '—'}
            </Title>
            <Text size="xs" c="dimmed" mt="xs">
              {activeStation?.last_check
                ? `Checked ${formatDateTime(activeStation.last_check)}`
                : 'Awaiting check'}
            </Text>
          </Card>
          <Card shadow="lg" radius="xl" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Stream preview
            </Text>
            {activeGroup?.entries[0]?.stream_url ? (
              <audio
                style={{ width: '100%', marginTop: 8 }}
                controls
                src={activeGroup.entries[0].stream_url ?? undefined}
              />
            ) : (
              <Text size="xs" c="dimmed" mt="xs">
                No stream URL available.
              </Text>
            )}
          </Card>
        </SimpleGrid>

        <Card shadow="lg" radius="xl" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
            Recent capture
          </Text>
          <Title order={4} mt="xs">
            {activeStation?.last_successful_capture
              ? formatDateTime(activeStation.last_successful_capture)
              : 'No capture yet'}
          </Title>
          <Text size="xs" c="dimmed" mt="xs">
            {activeStation?.speech_ratio !== null && activeStation?.speech_ratio !== undefined
              ? `${formatNumber(activeStation.speech_ratio * 60, 1)} min speech per hour`
              : 'Speech ratio not available'}
          </Text>
          {activeGroup?.entries.length ? (
            <Stack gap={4} mt="sm">
              <Text size="xs" c="dimmed">
                Streams in group: {activeGroup.entries.length}
              </Text>
              {activeGroup.entries.slice(0, 3).map((entry) => (
                <Text key={entry.id} size="xs" c="cyan.3">
                  {entry.stream_url ?? entry.homepage ?? 'Stream URL unavailable'}
                </Text>
              ))}
            </Stack>
          ) : null}
        </Card>

        <Card shadow="lg" radius="xl" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
            Language ID stack
          </Text>
          <Stack gap={4} mt="xs">
            <Text size="sm" c="dimmed">
              Audio LID: SpeechBrain VoxLingua107 (107 languages).
            </Text>
            <Text size="sm" c="dimmed">
              Text LID: fastText lid.176 when transcripts are available.
            </Text>
            <Text size="xs" c="dimmed">
              LID confidence is stored on each segment; station mix is aggregated hourly.
            </Text>
          </Stack>
        </Card>
      </Stack>
      <StationDrawer
        opened={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        groupName={activeGroup?.name ?? 'Station detail'}
        entries={activeGroup?.entries ?? []}
      />
    </SimpleGrid>
  )
}
