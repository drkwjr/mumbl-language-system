import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Card,
  Group,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import type { ColumnDef } from '@tanstack/react-table'
import { Filter, Search } from 'lucide-react'
import { api, type SegmentRow, type SegmentSearchResponse } from '../lib/api'
import { formatDateTime, formatNumber, formatPercent } from '../lib/format'
import { SegmentInspector } from '../components/segments/SegmentInspector'

const columnHelper = createColumnHelper<SegmentRow>()

const columns: ColumnDef<SegmentRow, string>[] = [
  columnHelper.accessor((row) => row.station_name, {
    id: 'station_name',
    header: 'Station',
  }),
  columnHelper.accessor((row) => row.primary_lang ?? '—', {
    id: 'primary_lang',
    header: 'Lang',
  }),
  columnHelper.accessor(
    (row) =>
      row.confidence !== null ? formatPercent(row.confidence, 1) : '—',
    {
      id: 'confidence',
      header: 'Confidence',
    },
  ),
  columnHelper.accessor((row) => `${formatNumber(row.duration, 1)}s`, {
    id: 'duration',
    header: 'Duration',
  }),
  columnHelper.accessor(
    (row) => (row.created_at ? formatDateTime(row.created_at) : '—'),
    {
      id: 'created_at',
      header: 'Created',
    },
  ),
]

const buildQueryParams = (filters: {
  lang: string
  confidenceMin: string
  stationId: string
}) => {
  const params = new URLSearchParams()
  if (filters.lang) params.set('lang', filters.lang)
  if (filters.confidenceMin) params.set('confidence_min', filters.confidenceMin)
  if (filters.stationId) params.set('station_id', filters.stationId)
  params.set('limit', '50')
  params.set('offset', '0')
  return params
}

export const SegmentsPage = () => {
  const [filters, setFilters] = useState({
    lang: '',
    confidenceMin: 0.75 as number | '',
    stationId: '',
  })
  const [selectedSegmentId, setSelectedSegmentId] = useState<number | null>(null)

  const queryParams = useMemo(() => buildQueryParams({
    lang: filters.lang,
    confidenceMin: filters.confidenceMin === '' ? '' : String(filters.confidenceMin),
    stationId: filters.stationId,
  }), [filters])

  const { data, isLoading } = useQuery<SegmentSearchResponse>({
    queryKey: ['segments-search', queryParams.toString()],
    queryFn: () => api.searchSegments(queryParams),
  })

  const table = useReactTable({
    data: data?.rows ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
      <Stack gap="md">
        <Card shadow="lg" radius="xl" withBorder>
          <Group gap="sm" align="center">
            <Filter className="h-4 w-4" />
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 2 }}>
              Segment filters
            </Text>
          </Group>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm" mt="md">
            <TextInput
              label="Language"
              placeholder="e.g. so"
              value={filters.lang}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, lang: event.currentTarget.value }))
              }
            />
            <NumberInput
              label="Min confidence"
              min={0}
              max={1}
              step={0.05}
              value={filters.confidenceMin}
              onChange={(value) =>
                setFilters((prev) => ({
                  ...prev,
                  confidenceMin: typeof value === 'number' ? value : '',
                }))
              }
            />
            <TextInput
              label="Station ID"
              placeholder="Optional"
              value={filters.stationId}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, stationId: event.currentTarget.value }))
              }
            />
          </SimpleGrid>
          <Group gap="xs" mt="md">
            <Search className="h-4 w-4" />
            <Text size="xs" c="dimmed">
              Showing {data?.total ?? 0} segments
            </Text>
          </Group>
        </Card>

        <Card shadow="lg" radius="xl" withBorder>
          <Title order={5} mb="sm">
            Segment table
          </Title>
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/40">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/80 text-xs uppercase tracking-[0.2em] text-slate-500">
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="px-3 py-2">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td className="px-3 py-4 text-sm text-slate-400" colSpan={columns.length}>
                      Loading segments…
                    </td>
                  </tr>
                ) : data?.total === 0 ? (
                  <tr>
                    <td className="px-3 py-4 text-sm text-slate-400" colSpan={columns.length}>
                      No segments yet. Run capture + LID to populate this table.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className="cursor-pointer border-t border-slate-800 hover:bg-slate-950/80"
                      onClick={() => setSelectedSegmentId(row.original.id)}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-3 py-3">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </Stack>

      <SegmentInspector segmentId={selectedSegmentId} />
    </SimpleGrid>
  )
}
