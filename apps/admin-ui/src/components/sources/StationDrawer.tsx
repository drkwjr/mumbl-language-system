import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Stack,
  Text,
} from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import {
  api,
  type PipelineActivityResponse,
  type StationListeningResponse,
  type StationQualityResponse,
  type StationSummary,
} from '../../lib/api'
import { formatDateTime, formatPercent } from '../../lib/format'

type StationDrawerProps = {
  opened: boolean
  onClose: () => void
  groupName: string
  entries: StationSummary[]
}

const getQuality = (bitrate?: number | null) => {
  if (!bitrate) return { label: 'Unknown', color: 'gray' }
  if (bitrate >= 128) return { label: 'High', color: 'green' }
  if (bitrate >= 64) return { label: 'Medium', color: 'yellow' }
  return { label: 'Low', color: 'red' }
}

const getHealthBadge = (status?: string | null) => {
  switch (status) {
    case 'healthy':
      return { label: 'Healthy', color: 'green' }
    case 'degraded':
      return { label: 'Degraded', color: 'yellow' }
    case 'down':
      return { label: 'Down', color: 'red' }
    default:
      return { label: 'Unknown', color: 'gray' }
  }
}

export const StationDrawer = ({ opened, onClose, groupName, entries }: StationDrawerProps) => {
  const primary = entries[0]
  const quality = getQuality(primary?.bitrate)
  const health = getHealthBadge(primary?.health_status)
  const stationId = primary?.id
  const frequencyLabel =
    primary?.frequency_label ??
    (primary?.frequency_mhz ? `${primary.frequency_mhz} FM` : null)
  const { data: activity } = useQuery<PipelineActivityResponse>({
    queryKey: ['station-activity', stationId],
    queryFn: () => api.getStationActivity(stationId ?? 0),
    enabled: opened && !!stationId,
    refetchInterval: 15_000,
  })
  const { data: listening } = useQuery<StationListeningResponse>({
    queryKey: ['station-listening', stationId],
    queryFn: () => api.getStationListening(stationId ?? 0),
    enabled: opened && !!stationId,
    refetchInterval: 60_000,
  })
  const { data: qualityStats } = useQuery<StationQualityResponse>({
    queryKey: ['station-quality', stationId],
    queryFn: () => api.getStationQuality(stationId ?? 0),
    enabled: opened && !!stationId,
    refetchInterval: 60_000,
  })

  const formatHours = (seconds?: number) =>
    seconds !== undefined ? (seconds / 3600).toFixed(1) : '0.0'

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="lg"
      title={groupName}
    >
      <Stack gap="md">
        <Group gap="sm">
          <Badge variant="light" color="cyan">
            {primary?.country ?? '—'}
          </Badge>
          <Badge variant="outline" color="gray">
            {primary?.lang_hint ?? 'no hint'}
          </Badge>
          {frequencyLabel ? (
            <Badge variant="light" color="blue">
              {frequencyLabel}
            </Badge>
          ) : null}
          <Badge variant="light" color={health.color}>
            {health.label}
          </Badge>
          <Badge variant="light" color={quality.color}>
            Audio {quality.label}
          </Badge>
        </Group>

        <Stack gap={4}>
          <Text size="sm" c="dimmed">
            Stream count: {entries.length}
          </Text>
          {frequencyLabel ? (
            <Text size="sm" c="dimmed">
              Frequency: {frequencyLabel}
              {primary?.frequency_source ? ` · ${primary.frequency_source}` : ''}
            </Text>
          ) : null}
          <Text size="sm" c="dimmed">
            Last check: {primary?.last_check ? formatDateTime(primary.last_check) : '—'}
          </Text>
          <Text size="sm" c="dimmed">
            Last success:{' '}
            {primary?.health_last_success_at
              ? formatDateTime(primary.health_last_success_at)
              : '—'}
          </Text>
          <Text size="sm" c="dimmed">
            Last failure:{' '}
            {primary?.health_last_failure_at
              ? formatDateTime(primary.health_last_failure_at)
              : '—'}
          </Text>
          {primary?.health_last_error ? (
            <Text size="sm" c="red.3">
              Error: {primary.health_last_error}
            </Text>
          ) : null}
        </Stack>

        <Divider />

        <Stack gap="xs">
          <Text size="sm" fw={600}>
            Stream preview
          </Text>
          {primary?.stream_url ? (
            <audio style={{ width: '100%' }} controls src={primary.stream_url ?? undefined} />
          ) : (
            <Text size="sm" c="dimmed">
              No stream URL available.
            </Text>
          )}
        </Stack>

        <Divider />

        <Stack gap="xs">
          <Text size="sm" fw={600}>
            Streams
          </Text>
          {entries.map((entry) => (
            <Stack key={entry.id} gap={2}>
              <Text size="xs" c="cyan.3">
                {entry.stream_url ?? entry.homepage ?? 'Stream URL unavailable'}
              </Text>
              <Text size="xs" c="dimmed">
                bitrate {entry.bitrate ?? '—'} kbps · codec {entry.codec ?? '—'}
              </Text>
            </Stack>
          ))}
        </Stack>

        <Divider />

        <Stack gap="xs">
          <Text size="sm" fw={600}>
            Status & notes
          </Text>
          <Text size="sm" c="dimmed">
            Speech ratio: {primary?.speech_ratio !== null && primary?.speech_ratio !== undefined
              ? formatPercent(primary.speech_ratio, 1)
              : '—'}
          </Text>
          <Text size="sm" c="dimmed">
            Avg bitrate:{' '}
            {qualityStats?.avg_bitrate_kbps !== null && qualityStats?.avg_bitrate_kbps !== undefined
              ? `${qualityStats.avg_bitrate_kbps.toFixed(1)} kbps`
              : '—'}
            {qualityStats?.bitrate_stddev_kbps !== null &&
            qualityStats?.bitrate_stddev_kbps !== undefined
              ? ` (σ ${qualityStats.bitrate_stddev_kbps.toFixed(1)})`
              : ''}
          </Text>
          <Text size="sm" c="dimmed">
            Dropouts: {qualityStats?.dropout_count ?? 0} · Silence:{' '}
            {qualityStats?.avg_silence_ratio !== null && qualityStats?.avg_silence_ratio !== undefined
              ? formatPercent(qualityStats.avg_silence_ratio, 1)
              : '—'}
          </Text>
          <Text size="sm" c="dimmed">
            Capture failures: {qualityStats?.capture_failures ?? 0} · FFmpeg errors:{' '}
            {qualityStats?.ffmpeg_errors ?? 0}
          </Text>
          <Text size="sm" c="dimmed">
            Last shard:{' '}
            {qualityStats?.last_shard_at ? formatDateTime(qualityStats.last_shard_at) : '—'}
          </Text>
          <Group gap="sm" mt="sm">
            <Button variant="light" disabled>
              Start capture run
            </Button>
            <Button variant="outline" disabled>
              View runs
            </Button>
            <Button variant="subtle" disabled>
              Add note
            </Button>
          </Group>
        </Stack>

        <Divider />

        <Stack gap="xs">
          <Text size="sm" fw={600}>
            Listening hours
          </Text>
          {listening ? (
            <Stack gap={6}>
              <Text size="sm" c="dimmed">
                Total: {formatHours(listening.totals.total_seconds)}h · Speech:{' '}
                {formatHours(listening.totals.speech_seconds)}h · Shards:{' '}
                {listening.totals.shard_count}
              </Text>
              <Group gap="sm">
                {Object.entries(listening.dayparts).map(([daypart, stats]) => (
                  <Badge key={daypart} variant="light" color="cyan">
                    {daypart}: {formatHours(stats.total_seconds)}h
                  </Badge>
                ))}
              </Group>
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">
              No listening data yet.
            </Text>
          )}
        </Stack>

        <Divider />

        <Stack gap="xs">
          <Text size="sm" fw={600}>
            Pipeline activity
          </Text>
          {activity && activity.stages.length > 0 ? (
            <Stack gap={6}>
              {activity.stages.map((stage) => (
                <Group key={stage.stage} justify="space-between">
                  <Text size="sm">{stage.stage}</Text>
                  <Text size="sm" c="dimmed">
                    {stage.last_seen ? formatDateTime(stage.last_seen) : '—'}
                  </Text>
                </Group>
              ))}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">
              No activity yet for this station.
            </Text>
          )}
        </Stack>

        <Divider />

        <Stack gap={4}>
          <Text size="sm" fw={600}>
            Language identification
          </Text>
          <Text size="sm" c="dimmed">
            Audio LID uses SpeechBrain VoxLingua107. Text LID uses fastText when
            transcripts exist. Confidence is stored per segment; station mix is aggregated hourly.
          </Text>
        </Stack>
      </Stack>
    </Drawer>
  )
}
