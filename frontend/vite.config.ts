import { defineConfig } from 'vite'

export default defineConfig(async () => {
  const plugin = await import('@vitejs/plugin-react')
  const react = plugin?.default || plugin
  return {
    plugins: [react()],
    server: { port: 5173 },
  }
})
