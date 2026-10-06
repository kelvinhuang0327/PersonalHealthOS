import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './pages/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#f6fbff',
        foreground: '#0f172a',
        primary: '#0ea5e9',
        success: '#22c55e',
      },
    },
  },
  plugins: [],
}

export default config
