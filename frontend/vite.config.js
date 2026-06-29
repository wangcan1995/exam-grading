import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端 API 代理，开发时前端 5173 → 后端 8000
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
