import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MantineProvider } from '@mantine/core'
import '@mantine/core/styles.css'
import './index.css'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <MantineProvider
        theme={{
          fontFamily: 'Space Grotesk, Sora, Segoe UI, sans-serif',
          headings: { fontFamily: 'Space Grotesk, Sora, Segoe UI, sans-serif' },
        }}
        defaultColorScheme="dark"
      >
        <App />
      </MantineProvider>
    </QueryClientProvider>
  </StrictMode>,
)
