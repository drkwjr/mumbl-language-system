import { useState } from 'react'
import {
  AppShell,
  Badge,
  Box,
  Burger,
  Group,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import type { NavItem, NavKey } from './SidebarNav'

type OpsShellProps = {
  currentView: NavKey
  onChangeView: (view: NavKey) => void
  navItems: NavItem[]
  title: string
  subtitle?: string
  freshnessLabel?: string
  children: React.ReactNode
}

export const OpsShell = ({
  currentView,
  onChangeView,
  navItems,
  title,
  subtitle,
  freshnessLabel,
  children,
}: OpsShellProps) => {
  const [opened, setOpened] = useState(false)

  return (
    <AppShell
      padding="lg"
      navbar={{ width: 260, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      header={{ height: 80 }}
      styles={{
        main: {
          background: 'linear-gradient(140deg, rgba(8,13,32,0.96), rgba(2,6,23,0.98))',
        },
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="lg" justify="space-between" align="center">
          <Group gap="md">
            <Burger
              opened={opened}
              onClick={() => setOpened((value) => !value)}
              hiddenFrom="sm"
              size="sm"
              aria-label="Toggle navigation"
            />
            <Box>
              <Text size="xs" c="cyan.3" tt="uppercase" fw={600} style={{ letterSpacing: 3 }}>
                Ops Dashboard
              </Text>
              <Title order={2} c="gray.0">
                {title}
              </Title>
              {subtitle ? (
                <Text size="sm" c="dimmed">
                  {subtitle}
                </Text>
              ) : null}
            </Box>
          </Group>
          <Group gap="sm">
            <Badge variant="outline" color="gray" size="lg">
              {new Date().toLocaleDateString()}
            </Badge>
            {freshnessLabel ? (
              <Badge color="cyan" variant="light" size="lg">
                {freshnessLabel}
              </Badge>
            ) : null}
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Stack gap="md" h="100%">
          <Box>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: 3 }}>
              Navigation
            </Text>
          </Box>
          <ScrollArea offsetScrollbars type="hover" style={{ flex: 1 }}>
            <Stack gap={4}>
              {navItems.map((item) => (
                <NavLink
                  key={item.key}
                  label={item.label}
                  leftSection={item.icon}
                  active={currentView === item.key}
                  onClick={() => onChangeView(item.key)}
                  variant="filled"
                />
              ))}
            </Stack>
          </ScrollArea>
          <Box>
            <Text size="xs" c="dimmed">
              Live feeds refresh every 15s. Manage sources in ingestion.
            </Text>
          </Box>
        </Stack>
      </AppShell.Navbar>

      <AppShell.Main>
        <Box py="md">{children}</Box>
      </AppShell.Main>
    </AppShell>
  )
}
